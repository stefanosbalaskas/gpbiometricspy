make_release_ready_pkg <- function(complete = TRUE) {
  path <- tempfile("gpbiometrics-release-ready-")
  dir.create(path, recursive = TRUE)
  dir.create(file.path(path, "R"), recursive = TRUE)
  dir.create(file.path(path, "man"), recursive = TRUE)
  dir.create(file.path(path, "tests", "testthat"), recursive = TRUE)
  dir.create(file.path(path, "docs", "reference"), recursive = TRUE)
  dir.create(file.path(path, "docs", "articles"), recursive = TRUE)

  writeLines(c(
    "Package: demoPkg",
    "Title: Demo Package",
    "Version: 0.0.1",
    "Description: Demo package for release-readiness tests.",
    "License: MIT"
  ), file.path(path, "DESCRIPTION"))

  writeLines(c("export(foo)", "export(bar)"), file.path(path, "NAMESPACE"))
  writeLines(c("foo <- function() 1", "bar <- function() 2"), file.path(path, "R", "functions.R"))
  writeLines("template:", file.path(path, "_pkgdown.yml"))
  writeLines("foo(); bar()", file.path(path, "tests", "testthat", "test-functions.R"))
  writeLines("<html>article</html>", file.path(path, "docs", "articles", "index.html"))

  writeLines("\\name{foo}\n\\alias{foo}\n\\title{foo}\n", file.path(path, "man", "foo.Rd"))
  writeLines("<html>foo</html>", file.path(path, "docs", "reference", "foo.html"))

  if (isTRUE(complete)) {
    writeLines("\\name{bar}\n\\alias{bar}\n\\title{bar}\n", file.path(path, "man", "bar.Rd"))
    writeLines("<html>bar</html>", file.path(path, "docs", "reference", "bar.html"))
  }

  path
}

test_that("audit_gazepoint_release_readiness passes a complete toy package", {
  path <- make_release_ready_pkg(complete = TRUE)

  audit <- audit_gazepoint_release_readiness(
    path = path,
    expected_exports = c("foo", "bar"),
    roadmap_terms = c("foo", "bar")
  )

  expect_s3_class(audit, "gazepoint_release_readiness_audit")
  expect_true(is.data.frame(audit$checks))
  expect_true(is.data.frame(audit$overview))
  expect_true(is.data.frame(audit$feature_coverage))
  expect_true(is.data.frame(audit$checklist))

  expect_equal(audit$overview$n_fail, 0)
  expect_true(audit$overview$release_ready)
  expect_false(audit$overview$needs_review)
  expect_true(all(c("foo", "bar") %in% audit$exports))

  expect_true(any(audit$checks$check == "expected_exports" & audit$checks$status == "pass"))
  expect_true(any(audit$checks$check == "export_manual_pages" & audit$checks$status == "pass"))
  expect_true(any(audit$checks$check == "export_reference_pages" & audit$checks$status == "pass"))
  expect_true(any(audit$checks$check == "roadmap_term_present" & audit$checks$status == "pass"))
})

test_that("audit_gazepoint_release_readiness reports conservative warnings and failures", {
  path <- make_release_ready_pkg(complete = FALSE)

  audit <- audit_gazepoint_release_readiness(
    path = path,
    expected_exports = c("foo", "bar", "missing_export"),
    roadmap_terms = c("foo", "bar", "missing_roadmap_term")
  )

  expect_s3_class(audit, "gazepoint_release_readiness_audit")
  expect_true(any(audit$checks$check == "expected_exports" & audit$checks$status == "fail"))
  expect_true(any(audit$checks$check == "export_manual_pages" & audit$checks$status == "warn"))
  expect_true(any(audit$checks$check == "export_reference_pages" & audit$checks$status == "warn"))
  expect_true(any(audit$checks$item == "missing_roadmap_term" & audit$checks$status == "warn"))
  expect_false(audit$overview$release_ready)
  expect_true(audit$overview$needs_review)
})

test_that("audit_gazepoint_release_readiness can make pkgdown coverage not checked", {
  path <- make_release_ready_pkg(complete = FALSE)

  audit <- audit_gazepoint_release_readiness(
    path = path,
    expected_exports = c("foo", "bar"),
    require_pkgdown = FALSE
  )

  pkgdown_row <- audit$checks[audit$checks$check == "export_reference_pages", , drop = FALSE]
  expect_equal(pkgdown_row$status, "not_checked")
})

test_that("summarize_gazepoint_feature_coverage uses narrow pupil and gaze matching", {
  exports <- c(
    "add_gazepoint_decision",
    "smooth_gazepoint_pupil",
    "detect_gazepoint_pupil_blinks",
    "plot_gazepoint_aoi_biometrics",
    "export_gazepoint_pipeline_dot"
  )

  coverage <- summarize_gazepoint_feature_coverage(exports = exports)

  expect_s3_class(coverage, "gazepoint_feature_coverage")
  expect_true("pupil_gaze" %in% coverage$domain)
  expect_equal(coverage$n_exports[coverage$domain == "pupil_gaze"], 3)
  expect_false(grepl("add_gazepoint_decision", coverage$examples[coverage$domain == "pupil_gaze"], fixed = TRUE))
})

test_that("summarize_gazepoint_feature_coverage supports custom patterns and empty exports", {
  coverage <- summarize_gazepoint_feature_coverage(
    exports = c("alpha_import", "beta_report", "gamma_report"),
    patterns = list(import = "import", report = "report")
  )

  expect_equal(coverage$n_exports[coverage$domain == "import"], 1)
  expect_equal(coverage$n_exports[coverage$domain == "report"], 2)

  empty <- summarize_gazepoint_feature_coverage(exports = character(), patterns = list(import = "import"))
  expect_equal(nrow(empty), 1)
  expect_equal(empty$n_exports, 0)
})

test_that("create_gazepoint_release_checklist works with and without audit evidence", {
  empty_checklist <- create_gazepoint_release_checklist(include_optional = FALSE)

  expect_s3_class(empty_checklist, "gazepoint_release_checklist")
  expect_equal(nrow(empty_checklist), 11)
  expect_true(all(empty_checklist$status == "not_checked"))

  checks <- data.frame(
    area = c("package_structure", "tests", "documentation", "pkgdown", "roadmap"),
    check = c("required_path", "export_test_references", "manual_files_present", "export_reference_pages", "roadmap_term_present"),
    item = c("DESCRIPTION", "exports", "man", "docs/reference", "scope"),
    status = c("pass", "warn", "pass", "pass", "pass"),
    message = c("ok", "review", "ok", "ok", "ok"),
    stringsAsFactors = FALSE
  )

  checklist <- create_gazepoint_release_checklist(checks, include_optional = FALSE)

  expect_s3_class(checklist, "gazepoint_release_checklist")
  expect_true(any(checklist$status == "warn"))
  expect_true(any(checklist$status == "pass"))
})

test_that("release-readiness helpers validate inputs", {
  expect_error(audit_gazepoint_release_readiness(path = ""), "path")
  expect_error(audit_gazepoint_release_readiness(path = tempfile()), "path")
  expect_error(audit_gazepoint_release_readiness(required_files = c("DESCRIPTION", "")), "required_files")
  expect_error(audit_gazepoint_release_readiness(expected_exports = c("foo", "")), "expected_exports")
  expect_error(audit_gazepoint_release_readiness(roadmap_terms = NA_character_), "roadmap_terms")
  expect_error(audit_gazepoint_release_readiness(require_pkgdown = NA), "require_pkgdown")

  expect_error(summarize_gazepoint_feature_coverage(path = ""), "path")
  expect_error(summarize_gazepoint_feature_coverage(exports = c("foo", "")), "exports")
  expect_error(summarize_gazepoint_feature_coverage(patterns = list(bad = c("a", "b"))), "single non-empty")
  expect_error(summarize_gazepoint_feature_coverage(patterns = stats::setNames(list("a"), "")), "patterns")

  expect_error(create_gazepoint_release_checklist(include_optional = NA), "include_optional")
})

test_that("release-readiness print methods return invisibly", {
  path <- make_release_ready_pkg(complete = TRUE)
  audit <- audit_gazepoint_release_readiness(path = path, expected_exports = c("foo", "bar"))
  coverage <- summarize_gazepoint_feature_coverage(path = path)
  checklist <- create_gazepoint_release_checklist(audit)

  expect_invisible(print(audit))
  expect_invisible(print(coverage))
  expect_invisible(print(checklist))
})
