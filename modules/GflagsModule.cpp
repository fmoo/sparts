/**
 * Copyright (c) 2014, Facebook, Inc.  All rights reserved.
 *
 * This source code is licensed under the BSD-style license found in the
 * LICENSE file in the root directory of this source tree. An additional grant
 * of patent rights can be found in the PATENTS file in the same directory.
 *
 * @author Tudor Bosman (tudorb@fb.com)
 */

#include <stdexcept>
#include <string>
#include <vector>

#include <boost/python.hpp>
#include <gflags/gflags.h>

#include "folly/Conv.h"
#include "folly/String.h"

namespace py = boost::python;

// Map flag type names to C++ types
#define X_FLAG_TYPES \
  X(bool, bool); \
  X(int32, int32_t); \
  X(int64, int64_t); \
  X(uint64, uint64_t); \
  X(double, double); \
  X(string, std::string);

/**
 * Return a Python object of appropriate type, given a flag type and
 * string value.
 */
py::object makeValue(const std::string& type, const std::string& value) {
#define X(tn, ty) if (type == #tn) return py::object(folly::to<ty>(value));
  X_FLAG_TYPES
#undef X
  throw std::runtime_error(folly::to<std::string>(
      "Unrecognized flag type: ", type));
}

std::string toString(const std::string& type, const py::object& value) {
#define X(tn, ty) \
  if (type == #tn) { \
    ty val = py::extract<ty>(value); \
    return folly::to<std::string>(std::move(val)); \
  }
  X_FLAG_TYPES
#undef X
  throw std::runtime_error(folly::to<std::string>(
      "Unrecognized flag type: ", type));
}

#undef X_FLAG_TYPES

using google::CommandLineFlagInfo;

/**
 * Retrieve the current value of a flag from a CommandLineFlagInfo object,
 * as the appropriate Python type.
 */
py::object getCurrentValue(CommandLineFlagInfo* info) {
  return makeValue(info->type, info->current_value);
}

/**
 * Retrieve the default value of a flag from a CommandLineFlagInfo object,
 * as the appropriate Python type.
 */
py::object getDefaultValue(CommandLineFlagInfo* info) {
  return makeValue(info->type, info->default_value);
}

namespace {
void doSetFlag(const char* name, const char* value,
               google::FlagSettingMode mode = google::SET_FLAGS_VALUE) {
  if (google::SetCommandLineOptionWithMode(name, value, mode).empty()) {
    PyErr_SetString(
        PyExc_ValueError,
        folly::to<std::string>("Flag setting failed: ", name).c_str());
    py::throw_error_already_set();
  }
}

CommandLineFlagInfo doGetFlag(const char* name) {
  CommandLineFlagInfo info;
  bool found = google::GetCommandLineFlagInfo(name, &info);
  if (!found) {
    PyErr_SetString(
        PyExc_KeyError,
        folly::to<std::string>("Flag not found: ", name).c_str());
    py::throw_error_already_set();
  }
  return info;
}
}  // namespace

/**
 * Retrieve the value of a given flag, raise KeyError if not found.
 */
py::object getFlag(const char* name) {
  auto info = doGetFlag(name);
  return getCurrentValue(&info);
}


/**
 * Set a flag to a given value.
 */
void setFlag(const char* name, py::object value, int mode) {
  if (mode != google::SET_FLAGS_VALUE &&
      mode != google::SET_FLAG_IF_DEFAULT &&
      mode != google::SET_FLAGS_DEFAULT) {
    PyErr_SetString(
        PyExc_ValueError,
        folly::to<std::string>("Invalid flag setting mode: ", mode).c_str());
    py::throw_error_already_set();
  }

  auto info = doGetFlag(name);
  doSetFlag(name, toString(info.type, value).c_str(),
            static_cast<google::FlagSettingMode>(mode));
}

/**
 * Reset a flag to default.
 */
void resetFlag(const char* name) {
  auto info = doGetFlag(name);
  if (info.current_value != info.default_value) {
    doSetFlag(name, info.default_value.c_str());
  }
}

/**
 * Retrieve a dictionary mapping each flag's name to a FlagInfo object.
 */
py::dict getAllFlags() {
  std::vector<CommandLineFlagInfo> flags;
  google::GetAllFlags(&flags);

  py::dict ret;
  for (auto& info : flags) {
    ret[info.name] = info;
  }

  return ret;
}

/**
 * Reset all flags to default.
 */
void resetAllFlags() {
  std::vector<CommandLineFlagInfo> flags;
  google::GetAllFlags(&flags);

  for (auto& info : flags) {
    if (info.current_value != info.default_value) {
      doSetFlag(info.name.c_str(), info.default_value.c_str());
    }
  }
}

/**
 * Return the version string.
 */
const char* getVersionString() {
  const char* versionString = google::VersionString();
  return versionString ?: "";
}


// Prettify errors
void translateException(const std::exception& exc) {
  PyErr_SetString(PyExc_RuntimeError, folly::exceptionStr(exc).c_str());
}

BOOST_PYTHON_MODULE(_sparts_gflags) {
  py::register_exception_translator<std::exception>(translateException);

  py::def("get_version_string", getVersionString,
          "Get version string.");
  py::def("get_flag", getFlag, py::args("name"),
          "Get value for one flag.");
  py::def("set_flag", setFlag,
          (py::arg("name"), py::arg("value"),
           py::arg("mode")=static_cast<int>(google::SET_FLAGS_VALUE)),
          "Set value for one flag.");
  py::def("reset_flag", resetFlag,
          py::args("name"),
          "Reset one flag to default.");
  py::def("get_all_flags", getAllFlags,
          "Get a dictionary mapping all flags to FlagInfo objects.");
  py::def("reset_all_flags", resetAllFlags,
          "Reset all flags to default.");

  // Export FlagSettingMode values
#define X(v) py::scope().attr(#v) = static_cast<int>(google::v);
  X(SET_FLAGS_VALUE);
  X(SET_FLAG_IF_DEFAULT);
  X(SET_FLAGS_DEFAULT);
#undef X

  // Export FlagInfo
  py::class_<CommandLineFlagInfo>("FlagInfo")
    .def_readonly("name", &CommandLineFlagInfo::name)
    .def_readonly("type", &CommandLineFlagInfo::type)
    .def_readonly("description", &CommandLineFlagInfo::description)
    .add_property("current_value", &getCurrentValue)
    .add_property("default_value", &getDefaultValue)
    .def_readonly("filename", &CommandLineFlagInfo::filename)
    .def_readonly("has_validator_fn", &CommandLineFlagInfo::has_validator_fn)
    .def_readonly("is_default", &CommandLineFlagInfo::is_default);
}
