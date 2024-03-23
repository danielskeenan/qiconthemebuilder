"""
freedesktop.org Icon Theme extractor.

Copyright (c) 2024
Distributed under the Boost Software License, Version 1.0.
(See accompanying file LICENSE.txt or copy at https://www.boost.org/LICENSE_1_0.txt)
"""

import argparse
import dataclasses
import hashlib
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from configparser import ConfigParser
from dataclasses import dataclass
from enum import StrEnum
from math import ceil
from pathlib import Path
from typing import Optional, List
from warnings import warn

ALLOWED_ICON_TYPES = frozenset(('.png', '.xpm', '.svg'))


class FreeDesktopConfigParser(ConfigParser):
    BOOLEAN_STATES = {'true': True, 'false': False}

    def __init__(self):
        super().__init__(
            delimiters=('=',),
            empty_lines_in_values=False,
            comment_prefixes=('#',),
        )

    def optionxform(self, optionstr):
        # Default config parser will force everything to lowercase.
        return optionstr


class IconType(StrEnum):
    FIXED = 'Fixed'
    SCALABLE = 'Scalable'
    THRESHOLD = 'Threshold'


@dataclass(frozen=True)
class IconProperties:
    size: int
    scale: int = 1
    # Context doesn't matter for this use case
    iconType: IconType = IconType.THRESHOLD
    maxSize: int = Optional[int]
    minSize: int = Optional[int]
    threshold: int = Optional[int]

    def to_hash(self):
        m = hashlib.sha256()
        m.update(self.size.to_bytes(4))
        m.update(self.scale.to_bytes(4))
        m.update(self.iconType.encode())
        m.update(0 if self.maxSize is None else self.maxSize.to_bytes(4))
        m.update(0 if self.minSize is None else self.minSize.to_bytes(4))
        m.update(0 if self.threshold is None else self.threshold.to_bytes(4))
        return m.hexdigest()


@dataclass
class Icon:
    path: Path
    props: IconProperties


@dataclass
class IconTheme:
    name: str
    path: Path
    icons: List[Icon] = dataclasses.field(default_factory=list)

    @classmethod
    def from_path(cls, path: Path):
        # Read index.theme
        if not (path / 'index.theme').is_file():
            raise RuntimeError('Source is missing index.theme')
        theme_parser = FreeDesktopConfigParser()
        theme_parser.read(path / 'index.theme', encoding='utf-8')
        if not theme_parser.has_section('Icon Theme'):
            raise RuntimeError('index.theme is missing Icon Theme section')
        theme_meta = theme_parser['Icon Theme']
        theme = cls(name=theme_meta['Name'], path=path)

        # Read directories
        scan_dirs = theme_meta['Directories'].split(',')
        if 'ScaledDirectories' in theme_meta:
            scan_dirs.extend(theme_meta['ScaledDirectories'].split(','))
        for rel_dir_path in scan_dirs:
            if not theme_parser.has_section(rel_dir_path):
                warn(RuntimeWarning('No section about {}'.format(rel_dir_path)))
                continue
            if not (path / rel_dir_path).resolve().is_dir():
                warn(RuntimeWarning('{} is not a directory'.format(rel_dir_path)))
                continue
            dir_meta = theme_parser[rel_dir_path]
            icon_size = dir_meta.get('Size')
            icon_scale = dir_meta.get('Scale', '1')
            icon_type = IconType(dir_meta.get('Type', fallback=IconType.THRESHOLD))
            icon_maxsize = dir_meta.get('MaxSize', fallback=icon_size)
            icon_minsize = dir_meta.get('MinSize', fallback=icon_size)
            icon_threshold = dir_meta.get('Threshold', fallback='2')

            # Load icons
            for icon_path in (path / rel_dir_path).resolve().iterdir():
                if icon_path.suffix not in ALLOWED_ICON_TYPES:
                    # Skip non-icons.
                    continue
                theme.icons.append(Icon(icon_path, IconProperties(
                    size=int(icon_size),
                    scale=int(icon_scale),
                    iconType=icon_type,
                    maxSize=int(icon_maxsize),
                    minSize=int(icon_minsize),
                    threshold=int(icon_threshold)
                )))

        return theme


def copy_icons(theme: IconTheme, dest: Path, patterns: List[re.Pattern]):
    if dest.is_dir():
        shutil.rmtree(dest)

    # Start building the QRC file.
    qrc = ET.ElementTree(ET.Element('RCC'))
    qresource = ET.SubElement(qrc.getroot(), 'qresource', {'prefix': '/icons/{}'.format(dest.stem)})

    # Find icons matching a pattern, copy to the destination, and save their properties for later.
    copied_props: dict[str, IconProperties] = {}
    directories = set()
    scaled_directories = set()
    for icon in theme.icons:
        match = None
        for pattern in patterns:
            if match := pattern.fullmatch(icon.path.stem):
                break
        if match is None:
            # Don't use this icon.
            continue
        props_hash = icon.props.to_hash()
        dest_dir = Path(props_hash)
        dest_rel_path = dest_dir / icon.path.name
        dest_path = dest / dest_rel_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        source_path = icon.path
        # This works better than follow_symlinks argument to shutil.copy() because that
        # can fall over if the symlink is relative.
        if source_path.is_symlink():
            source_path = icon.path.parent / source_path.readlink()
        shutil.copy(source_path, dest_path)
        qrc_file = ET.SubElement(qresource, 'file')
        qrc_file.text = str(dest_rel_path)
        if props_hash not in copied_props:
            copied_props[props_hash] = icon.props
        if icon.props.scale == 1:
            directories.add(str(dest_dir))
        else:
            scaled_directories.add(str(dest_dir))

    # Build new index.theme file.
    theme_meta = FreeDesktopConfigParser()
    theme_meta['Icon Theme'] = {
        'Name': theme.name,
        'Comment': 'Generated',
        'Directories': ','.join(directories)
    }
    if len(scaled_directories) > 0:
        theme_meta['Icon Theme']['ScaledDirectories'] = ','.join(scaled_directories)
    for (props_hash, props) in copied_props.items():
        dir_meta = {
            'Size': props.size
        }
        if props.scale != 1:
            dir_meta['Scale'] = props.scale
        if props.iconType != IconType.THRESHOLD:
            dir_meta['Type'] = props.iconType
        if props.iconType == IconType.FIXED:
            if props.maxSize != props.size:
                dir_meta['MaxSize'] = props.maxSize
            if props.minSize != props.size:
                dir_meta['MinSize'] = props.minSize
        elif props.iconType == IconType.THRESHOLD and props.threshold != 2:
            dir_meta['Threshold'] = props.threshold
        theme_meta[props_hash] = dir_meta
    with (dest / 'index.theme').open('wt', encoding='utf-8') as index_theme_f:
        theme_meta.write(index_theme_f, space_around_delimiters=False)

    # Write finalized QRC file.
    qrc_file = ET.SubElement(qresource, 'file')
    qrc_file.text = 'index.theme'
    qrc.write(dest / '{}.qrc'.format(dest.stem), encoding='utf-8', xml_declaration=True)


def main():
    args = argparse.ArgumentParser(
        description='Generate a partial freedesktop.org Icon Theme from an existing theme for use with QIcon.\n'
                    'See https://standards.freedesktop.org/icon-theme-spec for a description of how themes are\n'
                    'formatted. See https://doc.qt.io/qt-6/qicon.html for QIcon usage.',
    )
    args.add_argument('source', type=Path, help='Path to source theme.')
    args.add_argument('dest', type=Path, help='Path to created theme.')
    args.add_argument('--name', help='Name of generated theme.')
    args.add_argument('patterns', type=re.compile, nargs='+', help='Regex patterns for icons to include.')

    args = args.parse_args()

    theme = IconTheme.from_path(args.source)
    if args.name is not None:
        theme.name = args.name
    copy_icons(theme, args.dest, args.patterns)

    return 0


if __name__ == '__main__':
    exit(main())
