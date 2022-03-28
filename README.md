# About

Modified `fmt` recipe

* supports sanitizers, see [https://github.com/google/sanitizers/wiki/MemorySanitizerLibcxxHowTo#instrumented-gtest](https://github.com/google/sanitizers/wiki/MemorySanitizerLibcxxHowTo#instrumented-gtest)
* uses `llvm_tools` conan package in builds with `LLVM_USE_SANITIZER`, see https://github.com/google/sanitizers/wiki/MemorySanitizerLibcxxHowTo#instrumented-gtest
* uses `llvm_tools` conan package in builds with libc++ (will be instrumented if `LLVM_USE_SANITIZER` enabled)
* etc.

NOTE: use `-s llvm_tools:build_type=Release` during `conan install`

## Local build

```bash
export VERBOSE=1
export CONAN_REVISIONS_ENABLED=1
export CONAN_VERBOSE_TRACEBACK=1
export CONAN_PRINT_RUN_COMMANDS=1
export CONAN_LOGGING_LEVEL=10

conan remote add conan-center https://api.bintray.com/conan/conan/conan-center False

export PKG_NAME=fmt/master@dev/stable

(CONAN_REVISIONS_ENABLED=1 \
    conan remove --force $PKG_NAME || true)

conan create . \
  dev/stable \
  -s build_type=Release \
  --profile clang \
  --build missing \
  --build cascade

conan upload $PKG_NAME \
  --all -r=conan-local \
  -c --retry 3 \
  --retry-wait 10 \
  --force

# clean build cache
conan remove "*" --build --force
```

## Build with sanitizers support

Use `-o llvm_tools:enable_tsan=True` and `-e *:compile_with_llvm_tools=True` like so:

```bash
export CC=$(find ~/.conan/data/llvm_tools/master/conan/stable/package/ -path "*bin/clang" | head -n 1)

export CXX=$(find ~/.conan/data/llvm_tools/master/conan/stable/package/ -path "*bin/clang++" | head -n 1)

export TSAN_OPTIONS="handle_segv=0:disable_coredump=0:abort_on_error=1:report_thread_leaks=0"

# make sure that env. var. TSAN_SYMBOLIZER_PATH points to llvm-symbolizer
# conan package llvm_tools provides llvm-symbolizer
# and prints its path during cmake configure step
# echo $TSAN_SYMBOLIZER_PATH
export TSAN_SYMBOLIZER_PATH=$(find ~/.conan/data/llvm_tools/master/conan/stable/package/ -path "*bin/llvm-symbolizer" | head -n 1)

export VERBOSE=1
export CONAN_REVISIONS_ENABLED=1
export CONAN_VERBOSE_TRACEBACK=1
export CONAN_PRINT_RUN_COMMANDS=1
export CONAN_LOGGING_LEVEL=10

# NOTE: NO `--profile` argument cause we use `CXX` env. var
conan create . \
  dev/stable \
  -s build_type=Debug \
  -s compiler=clang \
  -s compiler.version=10 \
  -s compiler.libcxx=libc++ \
  -s llvm_tools:compiler=clang \
  -s llvm_tools:compiler.version=6.0 \
  -s llvm_tools:compiler.libcxx=libstdc++11 \
  -s llvm_tools:build_type=Release \
  -o llvm_tools:enable_tsan=True \
  -o llvm_tools:include_what_you_use=False \
  -e conan_fmt_test_package:compile_with_llvm_tools=True \
  -e conan_fmt_test_package:enable_llvm_tools=True \
  -e fmt:compile_with_llvm_tools=True \
  -e fmt:enable_llvm_tools=True \
  -o fmt:enable_tsan=True

# clean build cache
conan remove "*" --build --force
```

## How to diagnose errors in conanfile (CONAN_PRINT_RUN_COMMANDS)

```bash
export VERBOSE=1
export CONAN_REVISIONS_ENABLED=1
export CONAN_VERBOSE_TRACEBACK=1
export CONAN_PRINT_RUN_COMMANDS=1
export CONAN_LOGGING_LEVEL=10

# NOTE: about `--keep-source` see https://bincrafters.github.io/2018/02/27/Updated-Conan-Package-Flow-1.1/
conan create . conan/stable -s build_type=Debug --profile clang --build missing --build cascade --keep-source
```
