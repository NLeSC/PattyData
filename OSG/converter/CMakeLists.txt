cmake_minimum_required(VERSION 2.6) 
project( ViaAppia )
set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} "${CMAKE_SOURCE_DIR}/CMakeModules/")
find_package(OpenSceneGraph REQUIRED osg osgUtil osgViewer osgGA osgDB)
find_package(LibLAS)

# boost
set(Boost_USE_STATIC_LIBS   ON)
set(Boost_USE_MULTITHREADED ON)
find_package(Boost 1.38 COMPONENTS program_options thread system REQUIRED)
link_directories(${Boost_LIBRARY_DIRS})

# Lib squish
SET(SQUISH_SRCS
	src/libsquish/squish.h
    src/libsquish/alpha.cpp
    src/libsquish/alpha.h
    src/libsquish/clusterfit.cpp
    src/libsquish/clusterfit.h
    src/libsquish/colourblock.cpp
    src/libsquish/colourblock.h
    src/libsquish/colourfit.cpp
    src/libsquish/colourfit.h
    src/libsquish/colourset.cpp
    src/libsquish/colourset.h
    src/libsquish/maths.cpp
    src/libsquish/maths.h
    src/libsquish/rangefit.cpp
    src/libsquish/rangefit.h
    src/libsquish/simd.h
    src/libsquish/simd_float.h
    src/libsquish/simd_sse.h
    src/libsquish/simd_ve.h
    src/libsquish/singlecolourfit.cpp
    src/libsquish/singlecolourfit.h
    src/libsquish/singlecolourlookup.inl
    src/libsquish/squish.cpp
    )

source_group("Libsquish" FILES ${SQUISH_SRCS})

add_executable( ViaAppia 
	${SQUISH_SRCS}
	src/FadingLOD.cpp
	src/main.cpp
	src/PointModelLod.cpp
	src/PointQuadTree.cpp
	src/QuadTreeUtils.cpp
	src/PointStreamGeometry.cpp
	src/FadingLOD.h
	src/PointModelLod.h
	src/PointQuadTree.h
	src/QuadTreeUtils.h
	src/PointStreamGeometry.h) 
include_directories(${OSG_INCLUDE_DIR}
					${LIBLAS_INCLUDE_DIR}
					${Boost_INCLUDE_DIR}) 
target_link_libraries( ViaAppia
		optimized ${OSG_LIBRARY}
		optimized ${OSGGA_LIBRARY}
		optimized ${OSGDB_LIBRARY}
		optimized ${OPENTHREADS_LIBRARY}
		optimized ${OSGVIEWER_LIBRARY}
		optimized ${OSGUTIL_LIBRARY}
		optimized ${LIBLAS_LIBRARY_RELEASE}) 
target_link_libraries( ViaAppia 
		debug ${OSG_LIBRARY_DEBUG}
		debug ${OSGGA_LIBRARY_DEBUG}
		debug ${OSGDB_LIBRARY_DEBUG}
		debug ${OPENTHREADS_LIBRARY_DEBUG}
		debug ${OSGVIEWER_LIBRARY_DEBUG}
		debug ${OSGUTIL_LIBRARY_DEBUG}
		debug ${LIBLAS_LIBRARY_DEBUG}) 
install(TARGETS ViaAppia RUNTIME DESTINATION ${CMAKE_INSTALL_PREFIX})