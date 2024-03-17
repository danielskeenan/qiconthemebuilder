find_package(Python3 COMPONENTS Interpreter REQUIRED)

# Usage: create_icon_theme(<theme_name> TARGET <exe_target_name> SOURCE <source_theme_dir> ICON_PATTERNS <icon_1> [<icon_2>...])
function(create_icon_theme ICONTHEME_NAME)
    # Verify args.
    cmake_parse_arguments(PARSE_ARGV 1 ICONTHEME
            ""
            "TARGET;SOURCE"
            "ICON_PATTERNS"
    )
    set(REQUIRED_ARGS TARGET SOURCE ICON_PATTERNS)
    foreach (REQUIRED_ARG ${REQUIRED_ARGS})
        if (NOT ICONTHEME_${REQUIRED_ARG})
            message(FATAL_ERROR "Required argument ${REQUIRED_ARG} missing.")
        endif ()
    endforeach ()
    if (NOT TARGET "${ICONTHEME_TARGET}")
        message(FATAL_ERROR "Target ${ICONTHEME_TARGET} does not exist.")
    endif ()

    set(theme_PREFIX "${CMAKE_CURRENT_BINARY_DIR}/icons/${ICONTHEME_NAME}")
    add_custom_command(OUTPUT "${theme_PREFIX}/${ICONTHEME_NAME}.qrc"
            COMMAND Python3::Interpreter "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/qiconthemebuilder.py" "--name=${ICONTHEME_NAME}" "${ICONTHEME_SOURCE}" "${theme_PREFIX}" ${ICONTHEME_ICON_PATTERNS}
            COMMENT "Building icon theme ${ICONTHEME_NAME}..."
            DEPENDS "${ICONTHEME_SOURCE}/index.theme"
            BYPRODUCTS "${theme_PREFIX}/index.theme"
            VERBATIM
            COMMAND_EXPAND_LISTS
    )
    target_sources(${ICONTHEME_TARGET} PRIVATE "${theme_PREFIX}/${ICONTHEME_NAME}.qrc")
endfunction()

# Creates build steps for breeze icons (https://invent.kde.org/frameworks/breeze-icons).
# When complete, sets breeze_icons_DIR to the icon's installation path. Below this
# directory are the "breeze" and "breeze-dark" icon themes.
function(build_breeze)
    include(ExternalProject)
    set(ecm_PREFIX "${PROJECT_BINARY_DIR}/_deps/ecm-prefix")
    ExternalProject_Add(ECM
            EXCLUDE_FROM_ALL
            GIT_REPOSITORY "https://invent.kde.org/frameworks/extra-cmake-modules.git"
            GIT_TAG "master"
            PREFIX "${ecm_PREFIX}"
            CMAKE_CACHE_ARGS "-DBUILD_TESTING:STRING=OFF" "-DCMAKE_INSTALL_PREFIX:STRING=${ecm_PREFIX}"
    )
    set(breeze_icons_PREFIX "${PROJECT_BINARY_DIR}/_deps/breeze_icons-prefix")
    set(breeze_icons_RESULT_DIR "${breeze_icons_PREFIX}/bin/data/icons")
    ExternalProject_Add(breeze_icons
            EXCLUDE_FROM_ALL
            GIT_REPOSITORY "https://invent.kde.org/frameworks/breeze-icons.git"
            GIT_TAG "master"
            DEPENDS "ECM"
            PREFIX "${breeze_icons_PREFIX}"
            CMAKE_CACHE_ARGS "-DECM_DIR:STRING=${ecm_PREFIX}/share/ECM/cmake" "-DCMAKE_INSTALL_PREFIX:STRING=${breeze_icons_PREFIX}"
            INSTALL_BYPRODUCTS "${breeze_icons_RESULT_DIR}/breeze/index.theme" "${breeze_icons_RESULT_DIR}/breeze-dark/index.theme"
    )
    set(breeze_icons_DIR "${breeze_icons_RESULT_DIR}" PARENT_SCOPE)
endfunction()
