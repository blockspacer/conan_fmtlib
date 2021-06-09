from conans import ConanFile, CMake, tools
from conans.errors import ConanInvalidConfiguration
import os

from conans import ConanFile, CMake, tools
from conans.errors import ConanInvalidConfiguration
import os
import glob

import glob
import os
from conans import ConanFile, CMake, tools
from conans.model.version import Version
from conans.errors import ConanInvalidConfiguration

from conans import ConanFile, CMake, tools, AutoToolsBuildEnvironment, RunEnvironment, python_requires
from conans.errors import ConanInvalidConfiguration, ConanException
from conans.tools import os_info
import os, re, stat, fnmatch, platform, glob, traceback, shutil
from functools import total_ordering

# if you using python less than 3 use from distutils import strtobool
from distutils.util import strtobool

conan_build_helper = python_requires("conan_build_helper/[~=0.0]@conan/stable")

# Users locally they get the 1.0.0 version,
# without defining any env-var at all,
# and CI servers will append the build number.
# USAGE
# version = get_version("1.0.0")
# BUILD_NUMBER=-pre1+build2 conan export-pkg . my_channel/release
def get_version(version):
    bn = os.getenv("BUILD_NUMBER")
    return (version + bn) if bn else version

class FmtConan(conan_build_helper.CMakePackage):
    name = "fmt"
    version = get_version("master")
    commit = "d8b92543017053a2b2c5ca901ea310e20690b137"
    homepage = "https://github.com/fmtlib/fmt"
    repo_url = 'https://github.com/fmtlib/fmt'
    description = "A safe and fast alternative to printf and IOStreams."
    topics = ("conan", "fmt", "format", "iostream", "printf")
    url = "https://github.com/conan-io/conan-center-index"
    license = "MIT"
    exports_sources = ["CMakeLists.txt", "patches/**"]
    generators = "cmake"
    settings = "os", "compiler", "build_type", "arch"

    options = {
      "enable_ubsan": [True, False],
      "enable_asan": [True, False],
      "enable_msan": [True, False],
      "enable_tsan": [True, False],
      "shared": [True, False],
      "header_only": [True, False],
      "fPIC": [True, False],
      "with_fmt_alias": [True, False]
    }

    default_options = {
      "enable_ubsan": False,
      "enable_asan": False,
      "enable_msan": False,
      "enable_tsan": False,
      "shared": False,
      "header_only": False,
      "fPIC": True,
      "with_fmt_alias": False
    }

    _cmake = None

    # sets cmake variables required to use clang 10 from conan
    def _is_compile_with_llvm_tools_enabled(self):
      return self._environ_option("COMPILE_WITH_LLVM_TOOLS", default = 'false')

    # installs clang 10 from conan
    def _is_llvm_tools_enabled(self):
      return self._environ_option("ENABLE_LLVM_TOOLS", default = 'false')

    @property
    def _source_subfolder(self):
        return "source_subfolder"

    @property
    def _build_subfolder(self):
        return "build_subfolder"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        lower_build_type = str(self.settings.build_type).lower()

        if lower_build_type != "release" and not self._is_llvm_tools_enabled():
            self.output.warn('enable llvm_tools for Debug builds')

        if self._is_compile_with_llvm_tools_enabled() and not self._is_llvm_tools_enabled():
            raise ConanInvalidConfiguration("llvm_tools must be enabled")

        if self.options.enable_ubsan \
           or self.options.enable_asan \
           or self.options.enable_msan \
           or self.options.enable_tsan:
            if not self._is_llvm_tools_enabled():
                raise ConanInvalidConfiguration("sanitizers require llvm_tools")

        if self.options.header_only:
            self.settings.clear()
            del self.options.fPIC
            del self.options.shared
        elif self.options.shared:
            del self.options.fPIC
            if self.settings.compiler == "Visual Studio" and "MT" in self.settings.compiler.runtime:
                raise ConanInvalidConfiguration("Visual Studio build for shared library with MT runtime is not supported")

    def source(self):
        #tools.get(**self.conan_data["sources"][self.version])
        #extracted_dir = self.name + "-" + self.version
        #os.rename(extracted_dir, self._source_subfolder)
        self.run('git clone --progress --branch {} --single-branch --recursive --recurse-submodules {} {}'.format(self.version, self.repo_url, self._source_subfolder))
        if self.commit:
            with tools.chdir(self._source_subfolder):
                self.run('git checkout {}'.format(self.commit))

    def _configure_cmake(self):
        if self._cmake:
            return self._cmake
        self._cmake = CMake(self)
        self._cmake.definitions["FMT_DOC"] = False
        self._cmake.definitions["FMT_TEST"] = False
        self._cmake.definitions["FMT_INSTALL"] = True
        self._cmake.definitions["FMT_LIB_DIR"] = "lib"

        self._cmake.definitions["ENABLE_UBSAN"] = 'ON'
        if not self.options.enable_ubsan:
            self._cmake.definitions["ENABLE_UBSAN"] = 'OFF'

        self._cmake.definitions["ENABLE_ASAN"] = 'ON'
        if not self.options.enable_asan:
            self._cmake.definitions["ENABLE_ASAN"] = 'OFF'

        self._cmake.definitions["ENABLE_MSAN"] = 'ON'
        if not self.options.enable_msan:
            self._cmake.definitions["ENABLE_MSAN"] = 'OFF'

        self._cmake.definitions["ENABLE_TSAN"] = 'ON'
        if not self.options.enable_tsan:
            self._cmake.definitions["ENABLE_TSAN"] = 'OFF'

        self.add_cmake_option(self._cmake, "COMPILE_WITH_LLVM_TOOLS", self._is_compile_with_llvm_tools_enabled())

        self._cmake.configure(build_folder=self._build_subfolder)
        return self._cmake

    def build_requirements(self):
        self.build_requires("cmake_platform_detection/master@conan/stable")
        self.build_requires("cmake_build_options/master@conan/stable")
        self.build_requires("cmake_helper_utils/master@conan/stable")

        if self.options.enable_tsan \
            or self.options.enable_msan \
            or self.options.enable_asan \
            or self.options.enable_ubsan:
          self.build_requires("cmake_sanitizers/master@conan/stable")

        # provides clang-tidy, clang-format, IWYU, scan-build, etc.
        if self._is_llvm_tools_enabled():
          self.build_requires("llvm_tools/master@conan/stable")

    def build(self):
        for patch in self.conan_data.get("patches", {}).get(self.version, []):
            tools.patch(**patch)
        if not self.options.header_only:
            cmake = self._configure_cmake()
            cmake.build()

    def package(self):
        self.copy("LICENSE.rst", dst="licenses", src=self._source_subfolder)
        if self.options.header_only:
            self.copy("*.h", dst="include", src=os.path.join(self._source_subfolder, "include"))
        else:
            cmake = self._configure_cmake()
            cmake.install()
            tools.rmdir(os.path.join(self.package_folder, "lib", "cmake"))
            tools.rmdir(os.path.join(self.package_folder, "lib", "pkgconfig"))
            tools.rmdir(os.path.join(self.package_folder, "share"))

    def package_id(self):
        if self.options.header_only:
            self.info.header_only()
        else:
            del self.info.options.with_fmt_alias

    def package_info(self):
        if self.options.header_only:
            self.cpp_info.components["fmt-header-only"].defines.append("FMT_HEADER_ONLY=1")
            if self.options.with_fmt_alias:
                self.cpp_info.components["fmt-header-only"].defines.append("FMT_STRING_ALIAS=1")
        else:
            self.cpp_info.libs = tools.collect_libs(self)
            if self.options.with_fmt_alias:
                self.cpp_info.defines.append("FMT_STRING_ALIAS=1")
            if self.options.shared:
                self.cpp_info.defines.append("FMT_SHARED")
