test_that("interoperability manifest has a stable contract", {
  manifest <- gazepoint_interoperability_manifest()

  required <- c(
    "target",
    "ecosystem",
    "dependency",
    "dependency_type",
    "minimum_tested_version",
    "version_policy",
    "test_group",
    "bridge_functions",
    "optional"
  )

  expect_s3_class(
    manifest,
    "gazepoint_interoperability_manifest"
  )

  expect_true(
    all(required %in% names(manifest))
  )

  expect_false(
    anyDuplicated(manifest$target) > 0L
  )

  expect_true(
    all(
      manifest$dependency_type %in%
        c(
          "r_package",
          "python_module",
          "standard"
        )
    )
  )

  expect_true(
    is.logical(manifest$optional)
  )

  expect_true(
    all(
      c(
        "eyetrackingR",
        "PupillometryR",
        "gazeR",
        "MNE-Python",
        "pylsl",
        "BioSPPy",
        "HeartPy",
        "pyHRV",
        "BIDS",
        "NumPy",
        "pandas"
      ) %in% manifest$target
    )
  )
})


test_that("all declared bridge functions are exported", {
  manifest <- gazepoint_interoperability_manifest()

  declared <- unique(
    unlist(
      lapply(
        manifest$bridge_functions,
        function(value) {
          if (
            is.na(value) ||
            !nzchar(trimws(value))
          ) {
            return(character())
          }

          trimws(
            strsplit(
              value,
              ";",
              fixed = TRUE
            )[[1L]]
          )
        }
      ),
      use.names = FALSE
    )
  )

  declared <- declared[
    nzchar(declared)
  ]

  exports <- getNamespaceExports(
    "gpbiometrics"
  )

  expect_setequal(
    setdiff(
      declared,
      exports
    ),
    character()
  )
})


test_that("dependency-free audit records optional packages safely", {
  audit <- audit_gazepoint_interoperability_versions(
    include_python = FALSE
  )

  expect_s3_class(
    audit,
    "gazepoint_interoperability_audit"
  )

  expect_named(
    audit,
    c(
      "results",
      "summary",
      "session",
      "manifest"
    )
  )

  expect_true(
    is.data.frame(audit$results)
  )

  expect_true(
    is.data.frame(audit$summary)
  )

  expect_true(
    is.data.frame(audit$session)
  )

  expect_true(
    isTRUE(
      audit$summary$overall_pass[[1L]]
    )
  )

  python_rows <-
    audit$results$dependency_type ==
    "python_module"

  expect_true(
    all(
      audit$results$status[python_rows] ==
        "not_checked"
    )
  )

  expect_true(
    all(
      audit$results$pass[python_rows]
    )
  )

  expect_true(
    all(
      audit$results$needs_review[python_rows]
    )
  )
})


test_that("an installed R dependency is version audited", {
  manifest <- data.frame(
    target = "base-utils-contract",
    ecosystem = "R",
    dependency = "utils",
    dependency_type = "r_package",
    minimum_tested_version = "0.0.1",
    version_policy = "floor",
    test_group = "unit-test",
    bridge_functions =
      "prepare_gazepoint_biosppy_input",
    optional = FALSE,
    stringsAsFactors = FALSE
  )

  audit <- audit_gazepoint_interoperability_versions(
    manifest = manifest,
    include_python = FALSE,
    strict = TRUE
  )

  expect_identical(
    audit$results$status[[1L]],
    "available"
  )

  expect_true(
    audit$results$pass[[1L]]
  )

  expect_false(
    audit$results$needs_review[[1L]]
  )
})


test_that("versions below the tested floor fail clearly", {
  manifest <- data.frame(
    target = "impossible-utils-floor",
    ecosystem = "R",
    dependency = "utils",
    dependency_type = "r_package",
    minimum_tested_version = "9999.0.0",
    version_policy = "floor",
    test_group = "unit-test",
    bridge_functions =
      "prepare_gazepoint_biosppy_input",
    optional = FALSE,
    stringsAsFactors = FALSE
  )

  audit <- audit_gazepoint_interoperability_versions(
    manifest = manifest,
    include_python = FALSE,
    strict = FALSE
  )

  expect_identical(
    audit$results$status[[1L]],
    "below_minimum"
  )

  expect_false(
    audit$results$pass[[1L]]
  )

  expect_false(
    audit$summary$overall_pass[[1L]]
  )

  expect_error(
    audit_gazepoint_interoperability_versions(
      manifest = manifest,
      include_python = FALSE,
      strict = TRUE
    ),
    "Interoperability audit failed"
  )
})


test_that("missing optional dependencies require review but do not fail", {
  manifest <- data.frame(
    target = "missing-optional-test-package",
    ecosystem = "R",
    dependency =
      "definitelyNotInstalledGpbiometricsTestPackage",
    dependency_type = "r_package",
    minimum_tested_version = NA_character_,
    version_policy = "current-installed",
    test_group = "unit-test",
    bridge_functions =
      "prepare_gazepoint_biosppy_input",
    optional = TRUE,
    stringsAsFactors = FALSE
  )

  audit <- audit_gazepoint_interoperability_versions(
    manifest = manifest,
    include_python = FALSE,
    strict = TRUE
  )

  expect_identical(
    audit$results$status[[1L]],
    "missing_dependency"
  )

  expect_true(
    audit$results$pass[[1L]]
  )

  expect_true(
    audit$results$needs_review[[1L]]
  )
})


test_that("missing bridge exports fail independently of dependencies", {
  manifest <- data.frame(
    target = "missing-bridge-test",
    ecosystem = "R",
    dependency = "utils",
    dependency_type = "r_package",
    minimum_tested_version = "0.0.1",
    version_policy = "floor",
    test_group = "unit-test",
    bridge_functions =
      "definitely_missing_gpbiometrics_bridge",
    optional = FALSE,
    stringsAsFactors = FALSE
  )

  audit <- audit_gazepoint_interoperability_versions(
    manifest = manifest,
    include_python = FALSE
  )

  expect_identical(
    audit$results$status[[1L]],
    "missing_bridge"
  )

  expect_false(
    audit$results$pass[[1L]]
  )

  expect_match(
    audit$results$missing_bridge_functions[[1L]],
    "definitely_missing_gpbiometrics_bridge"
  )
})


test_that("Python checks can be disabled without initialization", {
  manifest <- data.frame(
    target = "python-test-module",
    ecosystem = "Python",
    dependency =
      "definitely_missing_python_distribution",
    dependency_type = "python_module",
    minimum_tested_version = "1.0.0",
    version_policy = "floor",
    test_group = "unit-test",
    bridge_functions = "",
    optional = TRUE,
    stringsAsFactors = FALSE
  )

  audit <- audit_gazepoint_interoperability_versions(
    manifest = manifest,
    include_python = FALSE,
    strict = TRUE
  )

  expect_identical(
    audit$results$status[[1L]],
    "not_checked"
  )

  expect_true(
    audit$results$pass[[1L]]
  )

  expect_true(
    audit$results$needs_review[[1L]]
  )
})


test_that("audit writer creates only aggregate machine-readable files", {
  audit <- audit_gazepoint_interoperability_versions(
    include_python = FALSE
  )

  output_dir <- tempfile(
    "gpbiometrics-interoperability-"
  )

  on.exit(
    unlink(
      output_dir,
      recursive = TRUE,
      force = TRUE
    ),
    add = TRUE
  )

  # Guarantee a clean first-write contract even after repeated tests.
  unlink(
    output_dir,
    recursive = TRUE,
    force = TRUE
  )

  files <- write_gazepoint_interoperability_audit(
    audit,
    output_dir
  )

  expect_length(
    files,
    4L
  )

  expect_named(
    files,
    c(
      "results",
      "summary",
      "session",
      "manifest"
    )
  )

  expect_true(
    all(file.exists(files))
  )

  expect_true(
    all(
      grepl(
        "\\.csv$",
        files
      )
    )
  )

  written_results <- utils::read.csv(
    files[["results"]],
    stringsAsFactors = FALSE
  )

  expect_true(
    all(
      c(
        "target",
        "dependency",
        "installed_version",
        "runtime_version",
        "operating_system",
        "status",
        "pass",
        "message",
        "timestamp_utc"
      ) %in% names(written_results)
    )
  )

  expect_false(
    any(
      c(
        "participant",
        "participant_id",
        "filename",
        "file_path",
        "data_path"
      ) %in% names(written_results)
    )
  )

  expect_error(
    write_gazepoint_interoperability_audit(
      audit,
      output_dir
    ),
    "Refusing to overwrite"
  )

  expect_silent(
    write_gazepoint_interoperability_audit(
      audit,
      output_dir,
      overwrite = TRUE
    )
  )
})
