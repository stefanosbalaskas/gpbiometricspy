test_that("numeric EDA vectors are prepared with an explicit rate", {
  out <- prepare_gazepoint_biosppy_input(
    c(1, 1.1, 1.2, 1.15),
    signal_type = "eda",
    sampling_rate_hz = 10
  )

  expect_s3_class(
    out,
    "gazepoint_biosppy_input"
  )

  expect_equal(
    out$vectors$all,
    c(1, 1.1, 1.2, 1.15)
  )

  expect_equal(
    unname(out$sampling_rates_hz["all"]),
    10
  )

  expect_equal(
    out$samples$time_s,
    c(0, 0.1, 0.2, 0.3)
  )

  expect_equal(
    out$settings$signal_type,
    "eda"
  )
})

test_that("EDA columns and sampling rates are detected", {
  data <- data.frame(
    time_s = seq(0, 0.4, by = 0.1),
    GSR = c(1, 1.1, 1.05, 1.2, 1.15)
  )

  out <- prepare_gazepoint_biosppy_input(
    data
  )

  expect_equal(
    out$settings$signal_type,
    "eda"
  )

  expect_equal(
    out$settings$signal_col,
    "GSR"
  )

  expect_equal(
    unname(out$sampling_rates_hz),
    10,
    tolerance = 1e-10
  )
})

test_that("grouped PPG vectors are prepared independently", {
  data <- data.frame(
    participant = rep(
      c("P01", "P02"),
      each = 4
    ),
    time_s = rep(
      c(0, 0.02, 0.04, 0.06),
      2
    ),
    HRP = c(
      1, 2, 3, 2,
      2, 3, 4, 3
    )
  )

  out <- prepare_gazepoint_biosppy_input(
    data,
    signal_type = "ppg",
    group_cols = "participant"
  )

  expect_named(
    out$vectors,
    c("P01", "P02")
  )

  expect_equal(
    out$vectors$P01,
    c(1, 2, 3, 2)
  )

  expect_equal(
    out$vectors$P02,
    c(2, 3, 4, 3)
  )

  expect_equal(
    unname(out$sampling_rates_hz),
    c(50, 50),
    tolerance = 1e-10
  )

  expect_equal(
    out$manifest$participant,
    c("P01", "P02")
  )
})

test_that("missing samples can be interpolated explicitly", {
  data <- data.frame(
    time_s = c(0, 1, 2, 3),
    EDA = c(1, NA, 3, 4)
  )

  out <- prepare_gazepoint_biosppy_input(
    data,
    signal_type = "eda",
    missing = "interpolate"
  )

  expect_equal(
    out$vectors$all,
    c(1, 2, 3, 4)
  )

  expect_equal(
    out$samples$interpolated,
    c(FALSE, TRUE, FALSE, FALSE)
  )

  expect_equal(
    out$manifest$interpolated_samples,
    1
  )

  expect_true(
    all(out$samples$included)
  )
})

test_that("missing samples fail under error handling", {
  data <- data.frame(
    time_s = c(0, 1, 2),
    EDA = c(1, NA, 3)
  )

  expect_error(
    prepare_gazepoint_biosppy_input(
      data,
      signal_type = "eda",
      missing = "error"
    ),
    "Non-finite signal"
  )
})

test_that("contiguous finite segments are exported separately", {
  data <- data.frame(
    time_s = 0:8,
    EDA = c(
      1, 2, 3,
      NA,
      4, 5, 6, 7,
      NA
    )
  )

  out <- prepare_gazepoint_biosppy_input(
    data,
    signal_type = "eda",
    missing = "segments",
    min_segment_samples = 3
  )

  expect_named(
    out$vectors,
    c(
      "all__segment_001",
      "all__segment_002"
    )
  )

  expect_equal(
    out$vectors[[1]],
    c(1, 2, 3)
  )

  expect_equal(
    out$vectors[[2]],
    c(4, 5, 6, 7)
  )

  expect_equal(
    nrow(out$manifest),
    2
  )

  expect_equal(
    out$samples$exclusion_reason[c(4, 9)],
    c(
      "missing_or_nonfinite",
      "missing_or_nonfinite"
    )
  )
})

test_that("short segments remain auditable but are excluded", {
  data <- data.frame(
    time_s = 0:6,
    PPG = c(
      1, 2,
      NA,
      3, 4, 5, 6
    )
  )

  out <- prepare_gazepoint_biosppy_input(
    data,
    signal_type = "ppg",
    missing = "segments",
    min_segment_samples = 3
  )

  expect_named(
    out$vectors,
    "all__segment_002"
  )

  expect_equal(
    out$samples$exclusion_reason[1:2],
    c("short_segment", "short_segment")
  )

  expect_false(
    any(out$samples$included[1:2])
  )
})

test_that("irregular sampling is rejected or allowed explicitly", {
  data <- data.frame(
    time_s = c(0, 0.1, 0.2, 0.5),
    EDA = c(1, 2, 3, 4)
  )

  expect_error(
    prepare_gazepoint_biosppy_input(
      data,
      signal_type = "eda"
    ),
    "Irregular sampling"
  )

  out <- prepare_gazepoint_biosppy_input(
    data,
    signal_type = "eda",
    irregular = "allow"
  )

  expect_equal(
    out$manifest$irregular_intervals_in_group,
    1
  )

  expect_true(
    out$manifest$maximum_relative_interval_error > 0
  )
})

test_that("BioSPPy-ready files and manifests are written", {
  output_dir <- tempfile(
    "biosppy-input-"
  )

  data <- data.frame(
    participant = rep(
      c("P01", "P02"),
      each = 3
    ),
    time_s = rep(
      c(0, 0.1, 0.2),
      2
    ),
    EDA = c(
      1, 1.1, 1.2,
      2, 2.1, 2.2
    )
  )

  out <- prepare_gazepoint_biosppy_input(
    data,
    signal_type = "eda",
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
    out$files$file_type == "signal" &
      out$files$vector_id == "P01"
  )

  expect_length(
    p01_row,
    1
  )

  expect_equal(
    readLines(
      out$files$path[p01_row],
      warn = FALSE
    ),
    c("1", "1.1", "1.2")
  )

  manifest_row <- which(
    out$files$file_type == "manifest"
  )

  manifest <- utils::read.csv(
    out$files$path[manifest_row],
    stringsAsFactors = FALSE
  )

  expect_equal(
    manifest$sample_count,
    c(3, 3)
  )

  unlink(
    output_dir,
    recursive = TRUE,
    force = TRUE
  )
})

test_that("existing output files are protected before writing", {
  output_dir <- tempfile(
    "biosppy-protect-"
  )

  dir.create(
    output_dir,
    recursive = TRUE
  )

  existing <- file.path(
    output_dir,
    "gazepoint_biosppy_eda_all.csv"
  )

  writeLines(
    "existing",
    existing
  )

  expect_error(
    prepare_gazepoint_biosppy_input(
      c(1, 2, 3),
      signal_type = "eda",
      sampling_rate_hz = 10,
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
      "gazepoint_biosppy_eda_manifest.csv"
    ))
  )

  unlink(
    output_dir,
    recursive = TRUE,
    force = TRUE
  )
})

test_that("input validation is explicit", {
  expect_error(
    prepare_gazepoint_biosppy_input(
      numeric(),
      signal_type = "eda",
      sampling_rate_hz = 10
    ),
    "at least one signal"
  )

  expect_error(
    prepare_gazepoint_biosppy_input(
      c(1, 2, 3),
      sampling_rate_hz = 10
    ),
    "requires"
  )

  expect_error(
    prepare_gazepoint_biosppy_input(
      c(1, 2, 3),
      signal_type = "eda"
    ),
    "sampling_rate_hz"
  )

  expect_error(
    prepare_gazepoint_biosppy_input(
      data.frame(
        time_s = 0:2,
        EDA = 1:3,
        PPG = 4:6
      )
    ),
    "Both EDA and PPG"
  )

  expect_error(
    prepare_gazepoint_biosppy_input(
      data.frame(
        time_s = c(0, 1, 0.5),
        EDA = 1:3
      ),
      signal_type = "eda"
    ),
    "strictly increasing"
  )

  expect_error(
    prepare_gazepoint_biosppy_input(
      data.frame(
        EDA = 1:3
      ),
      signal_type = "eda"
    ),
    "time_col"
  )

  expect_error(
    prepare_gazepoint_biosppy_input(
      data.frame(
        time_s = 0:2,
        EDA = c("1", "2", "3")
      ),
      signal_type = "eda"
    ),
    "numeric"
  )
})
