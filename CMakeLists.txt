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
    include(FetchContent)
    FetchContent_Declare(ECM
            GIT_REPOSITORY "https://invent.kde.org/frameworks/extra-cmake-modules.git"
            GIT_TAG "master"
    )
    FetchContent_Populate(ECM)
    set(ECM_INSTALL_DIR "${FETCHCONTENT_BASE_DIR}/ecm-install")
    message(STATUS "Building ECM...")
    execute_process(
            COMMAND "${CMAKE_COMMAND}" -B "${ECM_BINARY_DIR}" -S "${ECM_SOURCE_DIR}"
            "-DBUILD_TESTING=OFF" "-DCMAKE_INSTALL_PREFIX=${ECM_INSTALL_DIR}"
            COMMAND_ERROR_IS_FATAL ANY
    )
    execute_process(
            COMMAND "${CMAKE_COMMAND}" --install "${ECM_BINARY_DIR}"
            COMMAND_ERROR_IS_FATAL ANY
    )
    FetchContent_Declare(breeze_icons
            GIT_REPOSITORY "https://invent.kde.org/frameworks/breeze-icons.git"
            GIT_TAG "master"
    )
    FetchContent_Populate(breeze_icons)
    set(breeze_icons_INSTALL_DIR "${FETCHCONTENT_BASE_DIR}/breeze_icons-install")
    message(STATUS "Building breeze_icons...")
    execute_process(
            COMMAND "${CMAKE_COMMAND}" -B "${breeze_icons_BINARY_DIR}" -S "${breeze_icons_SOURCE_DIR}"
            "-DECM_DIR=${ECM_INSTALL_DIR}/share/ECM/cmake" "-DQt6_DIR=${Qt6_DIR}"
            "-DCMAKE_INSTALL_PREFIX=${breeze_icons_INSTALL_DIR}"
            COMMAND_ERROR_IS_FATAL ANY
    )
    execute_process(
            COMMAND "${CMAKE_COMMAND}" --install "${breeze_icons_BINARY_DIR}"
            COMMAND_ERROR_IS_FATAL ANY
    )
    set(breeze_icons_DIR "${breeze_icons_INSTALL_DIR}/bin/data/icons" PARENT_SCOPE)
endfunction()
