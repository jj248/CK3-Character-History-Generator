#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "graphviz::cdt" for configuration "Release"
set_property(TARGET graphviz::cdt APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(graphviz::cdt PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/lib/cdt.lib"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/cdt.dll"
  )

list(APPEND _cmake_import_check_targets graphviz::cdt )
list(APPEND _cmake_import_check_files_for_graphviz::cdt "${_IMPORT_PREFIX}/lib/cdt.lib" "${_IMPORT_PREFIX}/bin/cdt.dll" )

# Import target "graphviz::gvpr" for configuration "Release"
set_property(TARGET graphviz::gvpr APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(graphviz::gvpr PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/lib/gvpr.lib"
  IMPORTED_LINK_DEPENDENT_LIBRARIES_RELEASE "graphviz::cgraph;graphviz::gvc"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/gvpr.dll"
  )

list(APPEND _cmake_import_check_targets graphviz::gvpr )
list(APPEND _cmake_import_check_files_for_graphviz::gvpr "${_IMPORT_PREFIX}/lib/gvpr.lib" "${_IMPORT_PREFIX}/bin/gvpr.dll" )

# Import target "graphviz::pathplan" for configuration "Release"
set_property(TARGET graphviz::pathplan APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(graphviz::pathplan PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/lib/pathplan.lib"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/pathplan.dll"
  )

list(APPEND _cmake_import_check_targets graphviz::pathplan )
list(APPEND _cmake_import_check_files_for_graphviz::pathplan "${_IMPORT_PREFIX}/lib/pathplan.lib" "${_IMPORT_PREFIX}/bin/pathplan.dll" )

# Import target "graphviz::xdot" for configuration "Release"
set_property(TARGET graphviz::xdot APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(graphviz::xdot PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/lib/xdot.lib"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/xdot.dll"
  )

list(APPEND _cmake_import_check_targets graphviz::xdot )
list(APPEND _cmake_import_check_files_for_graphviz::xdot "${_IMPORT_PREFIX}/lib/xdot.lib" "${_IMPORT_PREFIX}/bin/xdot.dll" )

# Import target "graphviz::cgraph" for configuration "Release"
set_property(TARGET graphviz::cgraph APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(graphviz::cgraph PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/lib/cgraph.lib"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/cgraph.dll"
  )

list(APPEND _cmake_import_check_targets graphviz::cgraph )
list(APPEND _cmake_import_check_files_for_graphviz::cgraph "${_IMPORT_PREFIX}/lib/cgraph.lib" "${_IMPORT_PREFIX}/bin/cgraph.dll" )

# Import target "graphviz::gvc" for configuration "Release"
set_property(TARGET graphviz::gvc APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(graphviz::gvc PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/lib/gvc.lib"
  IMPORTED_LINK_DEPENDENT_LIBRARIES_RELEASE "graphviz::cdt;graphviz::cgraph"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/gvc.dll"
  )

list(APPEND _cmake_import_check_targets graphviz::gvc )
list(APPEND _cmake_import_check_files_for_graphviz::gvc "${_IMPORT_PREFIX}/lib/gvc.lib" "${_IMPORT_PREFIX}/bin/gvc.dll" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
