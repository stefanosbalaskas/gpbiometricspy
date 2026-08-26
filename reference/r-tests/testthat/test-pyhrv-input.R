test_that("prepare_gazepoint_pyhrv_input converts seconds to milliseconds", {
  out <- prepare_gazepoint_pyhrv_input(
    c(0.8, 0.81, 0.79),
    unit = "seconds"
  )

  expect_s3_class(
    out,
    "gazepoint_pyhrv_input"
  )

  expect_equal(
    out$vectors$all,
    c(800, 810, 790)
  )

  expect_equal(
    out$intervals$nni_ms,
    c(800, 810, 790)
  )

  expect_equal(
    out$intervals$interval_end_time_s,
    c(0.8, 1.61, 2.4)
  )

  expect_equal(
    out$settings$resolved_unit,
    "seconds"
  )
})

test_that("prepare_gazepoint_pyhrv_input supports grouped data", {
  intervals <- data.frame(
    participant = c(
      "P01",
      "P01",
      "P02",
      "P02"
    ),
    IBI_clean_ms = c(
      800,
      810,
      900,
      910
    )
  )

  out <- prepare_gazepoint_pyhrv_input(
    intervals,
    group_cols = "participant"
  )

  expect_named(
    out$vectors,
    c("P01", "P02")
  )

  expect_equal(
    out$vectors$P01,
    c(800, 810)
  )

  expect_equal(
    out$vectors$P02,
    c(900, 910)
  )

  expect_equal(
    out$manifest$included_intervals,
    c(2, 2)
  )

  expect_equal(
    out$manifest$participant,
    c("P01", "P02")
  )
})

test_that("plausibility filtering is explicit and auditable", {
  intervals <- data.frame(
    IBI = c(
      800,
      200,
      2500,
      NA,
      -10,
      900
    )
  )

  out <- prepare_gazepoint_pyhrv_input(
    intervals,
    unit = "milliseconds",
    filter = "plausible",
    min_nni_ms = 300,
    max_nni_ms = 2000
  )

  expect_equal(
    out$vectors$all,
    c(800, 900)
  )

  expect_equal(
    out$intervals$interval_status,
    c(
      "plausible",
      "below_minimum",
      "above_maximum",
      "missing_or_nonfinite",
      "non_positive",
      "plausible"
    )
  )

  expect_equal(
    out$manifest$included_intervals,
    2
  )

  expect_equal(
    out$manifest$excluded_intervals,
    4
  )

  expect_equal(
    out$manifest$excluded_below_minimum,
    1
  )

  expect_equal(
    out$manifest$excluded_above_maximum,
    1
  )
})

test_that("filter none retains finite positive out-of-range intervals", {
  intervals <- c(
    200,
    800,
    2500,
    NA,
    0
  )

  out <- prepare_gazepoint_pyhrv_input(
    intervals,
    unit = "milliseconds",
    filter = "none"
  )

  expect_equal(
    out$vectors$all,
    c(200, 800, 2500)
  )

  expect_equal(
    out$intervals$interval_status,
    c(
      "below_minimum",
      "plausible",
      "above_maximum",
      "missing_or_nonfinite",
      "non_positive"
    )
  )

  expect_true(
    all(is.na(
      out$intervals$exclusion_reason[1:3]
    ))
  )
})

test_that("repeated sample-level interval values can be collapsed", {
  intervals <- data.frame(
    participant = "P01",
    IBI_clean_ms = c(
      800,
      800,
      800,
      810,
      810,
      790
    )
  )

  out <- prepare_gazepoint_pyhrv_input(
    intervals,
    group_cols = "participant",
    collapse_repeated_intervals = TRUE
  )

  expect_equal(
    out$vectors$P01,
    c(800, 810, 790)
  )

  expect_equal(
    out$intervals$repeated_interval,
    c(
      FALSE,
      TRUE,
      TRUE,
      FALSE,
      TRUE,
      FALSE
    )
  )

  expect_equal(
    out$manifest$excluded_repeated,
    3
  )
})

test_that("repeated intervals are evaluated independently by group", {
  intervals <- data.frame(
    participant = c(
      "P01",
      "P01",
      "P02",
      "P02"
    ),
    IBI_clean_ms = c(
      800,
      800,
      800,
      800
    )
  )

  out <- prepare_gazepoint_pyhrv_input(
    intervals,
    group_cols = "participant",
    collapse_repeated_intervals = TRUE
  )

  expect_equal(
    out$vectors$P01,
    800
  )

  expect_equal(
    out$vectors$P02,
    800
  )

  expect_equal(
    out$intervals$repeated_interval,
    c(
      FALSE,
      TRUE,
      FALSE,
      TRUE
    )
  )
})

test_that("automatic unit assessment uses names and values", {
  milliseconds <- data.frame(
    RR_ms = c(800, 810)
  )

  seconds <- data.frame(
    IBI = c(0.8, 0.81)
  )

  out_ms <- prepare_gazepoint_pyhrv_input(
    milliseconds
  )

  out_s <- prepare_gazepoint_pyhrv_input(
    seconds
  )

  expect_equal(
    out_ms$settings$resolved_unit,
    "milliseconds"
  )

  expect_equal(
    out_ms$settings$unit_resolution_method,
    "column_name"
  )

  expect_equal(
    out_s$settings$resolved_unit,
    "seconds"
  )

  expect_equal(
    out_s$settings$unit_resolution_method,
    "median_heuristic"
  )

  expect_equal(
    out_s$vectors$all,
    c(800, 810)
  )
})

test_that("automatic unit assessment rejects ambiguous scales", {
  expect_error(
    prepare_gazepoint_pyhrv_input(
      c(20, 30, 40),
      unit = "auto"
    ),
    "ambiguous"
  )
})

test_that("prepare_gazepoint_pyhrv_input writes Python-ready files", {
  output_dir <- tempfile(
    "pyhrv-input-"
  )

  intervals <- data.frame(
    participant = c(
      "P01",
      "P01",
      "P02",
      "P02"
    ),
    IBI_clean_ms = c(
      800,
      810,
      900,
      910
    )
  )

  out <- prepare_gazepoint_pyhrv_input(
    intervals,
    group_cols = "participant",
    output_dir = output_dir,
    prefix = "study"
  )

  expect_equal(
    nrow(out$files),
    3
  )

  expect_true(
    all(file.exists(out$files$path))
  )

  p01_row <- which(
    out$files$file_type == "intervals" &
      out$files$group_id == "P01"
  )

  expect_length(
    p01_row,
    1
  )

  p01_lines <- readLines(
    out$files$path[p01_row],
    warn = FALSE
  )

  expect_equal(
    p01_lines,
    c("800", "810")
  )

  manifest_row <- which(
    out$files$file_type == "manifest"
  )

  expect_length(
    manifest_row,
    1
  )

  manifest <- utils::read.csv(
    out$files$path[manifest_row],
    stringsAsFactors = FALSE
  )

  expect_equal(
    manifest$included_intervals,
    c(2, 2)
  )

  unlink(
    output_dir,
    recursive = TRUE,
    force = TRUE
  )
})

test_that("existing output files are protected before writing", {
  output_dir <- tempfile(
    "pyhrv-protect-"
  )

  dir.create(
    output_dir,
    recursive = TRUE
  )

  existing <- file.path(
    output_dir,
    "gazepoint_pyhrv.csv"
  )

  writeLines(
    "existing",
    existing
  )

  expect_error(
    prepare_gazepoint_pyhrv_input(
      c(800, 810),
      unit = "milliseconds",
      output_dir = output_dir
    ),
    "already exists"
  )

  expect_equal(
    readLines(
      existing,
      warn = FALSE
    ),
    "existing"
  )

  expect_false(
    file.exists(file.path(
      output_dir,
      "gazepoint_pyhrv_manifest.csv"
    ))
  )

  unlink(
    output_dir,
    recursive = TRUE,
    force = TRUE
  )
})

test_that("prepare_gazepoint_pyhrv_input validates inputs", {
  expect_error(
    prepare_gazepoint_pyhrv_input(
      numeric(),
      unit = "milliseconds"
    ),
    "at least one interval"
  )

  expect_error(
    prepare_gazepoint_pyhrv_input(
      data.frame(
        IBI = c("800", "810")
      )
    ),
    "numeric"
  )

  expect_error(
    prepare_gazepoint_pyhrv_input(
      data.frame(
        IBI = c(800, 810)
      ),
      group_cols = "participant"
    ),
    "not found"
  )

  expect_error(
    prepare_gazepoint_pyhrv_input(
      c(800, 810),
      group_cols = "participant",
      unit = "milliseconds"
    ),
    "cannot be used"
  )

  expect_error(
    prepare_gazepoint_pyhrv_input(
      c(800, 810),
      unit = "milliseconds",
      min_nni_ms = 2000,
      max_nni_ms = 300
    ),
    "greater"
  )

  expect_error(
    prepare_gazepoint_pyhrv_input(
      c(800, 810),
      unit = "milliseconds",
      repeated_tolerance_ms = -1
    ),
    "non-negative"
  )
})
