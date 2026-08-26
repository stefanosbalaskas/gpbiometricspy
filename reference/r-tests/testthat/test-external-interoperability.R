test_that("export_gazepoint_rhrv_input prepares beat tables", {
  dat <- data.frame(
    participant = "P1",
    IBI_clean_ms = c(1000, 1000, 1020, 1020, 980)
  )

  res <- export_gazepoint_rhrv_input(
    dat,
    ibi_col = "IBI_clean_ms",
    group_cols = "participant",
    collapse_repeated_intervals = TRUE
  )

  expect_s3_class(res, "gazepoint_rhrv_input_export")
  expect_equal(res$overview$status, "rhrv_input_prepared")
  expect_equal(res$overview$beat_rows, 3)
  expect_equal(res$beat_table$ibi_ms, c(1000, 1020, 980))
  expect_true(all(c("time_s", "ibi_ms", "ibi_s") %in% names(res$beat_table)))
})

test_that("export_gazepoint_rhrv_input can retain repeated intervals", {
  dat <- data.frame(
    participant = "P1",
    IBI_clean_ms = c(1000, 1000, 1020)
  )

  res <- export_gazepoint_rhrv_input(
    dat,
    ibi_col = "IBI_clean_ms",
    group_cols = "participant",
    collapse_repeated_intervals = FALSE
  )

  expect_equal(res$overview$beat_rows, 3)
  expect_equal(res$beat_table$used_intervals_after_collapse[1], 3)
})

test_that("export_gazepoint_rhrv_input writes group files", {
  dat <- data.frame(
    participant = c("P1", "P1", "P2", "P2"),
    IBI_clean_ms = c(1000, 1020, 900, 910)
  )

  out_dir <- tempfile("rhrv_export_")

  res <- export_gazepoint_rhrv_input(
    dat,
    ibi_col = "IBI_clean_ms",
    group_cols = "participant",
    output_dir = out_dir
  )

  expect_equal(res$overview$status, "rhrv_input_exported")
  expect_equal(sum(file.exists(res$manifest$file_path)), 2)

  unlink(out_dir, recursive = TRUE, force = TRUE)
})

test_that("prepare_gazepoint_neurokit_eda_input prepares EDA tables", {
  dat <- data.frame(
    participant = "P1",
    CNT = 0:4,
    GSR_US = c(1, 1.1, 1.2, 1.1, 1.0)
  )

  res <- prepare_gazepoint_neurokit_eda_input(
    dat,
    eda_col = "GSR_US",
    time_col = "CNT",
    group_cols = "participant",
    sampling_rate = 10
  )

  expect_s3_class(res, "gazepoint_neurokit_eda_input")
  expect_equal(res$overview$status, "neurokit_eda_input_prepared")
  expect_equal(res$overview$eda_rows, 5)
  expect_equal(res$eda_table$time_s, c(0, 0.1, 0.2, 0.3, 0.4))
})

test_that("prepare_gazepoint_neurokit_eda_input writes group files", {
  dat <- data.frame(
    participant = c("P1", "P1", "P2", "P2"),
    CNT = c(0, 1, 0, 1),
    GSR_US = c(1, 2, 3, 4)
  )

  out_dir <- tempfile("eda_export_")

  res <- prepare_gazepoint_neurokit_eda_input(
    dat,
    eda_col = "GSR_US",
    time_col = "CNT",
    group_cols = "participant",
    output_dir = out_dir
  )

  expect_equal(res$overview$status, "neurokit_eda_input_exported")
  expect_equal(sum(file.exists(res$manifest$file_path)), 2)

  unlink(out_dir, recursive = TRUE, force = TRUE)
})

test_that("run_gazepoint_neurokit_eda_crosscheck skips by default", {
  dat <- data.frame(
    participant = "P1",
    CNT = 0:4,
    GSR_US = c(1, 1.1, 1.2, 1.1, 1.0)
  )

  res <- run_gazepoint_neurokit_eda_crosscheck(
    dat,
    eda_col = "GSR_US",
    time_col = "CNT",
    group_cols = "participant",
    sampling_rate = 10,
    execute = FALSE
  )

  expect_s3_class(res, "gazepoint_neurokit_eda_crosscheck")
  expect_equal(res$overview$status, "skipped_execute_false")
  expect_false(res$overview$executed)
  expect_s3_class(res$prepared_input, "gazepoint_neurokit_eda_input")
})

test_that("run_gazepoint_neurokit_eda_crosscheck accepts prepared input", {
  dat <- data.frame(
    participant = "P1",
    CNT = 0:4,
    GSR_US = c(1, 1.1, 1.2, 1.1, 1.0)
  )

  prepared <- prepare_gazepoint_neurokit_eda_input(
    dat,
    eda_col = "GSR_US",
    time_col = "CNT",
    group_cols = "participant",
    sampling_rate = 10
  )

  res <- run_gazepoint_neurokit_eda_crosscheck(
    prepared,
    sampling_rate = 10,
    execute = FALSE
  )

  expect_equal(res$overview$status, "skipped_execute_false")
  expect_equal(res$overview$input_rows, 5)
})

test_that("external interoperability helpers validate inputs", {
  dat <- data.frame(
    participant = "P1",
    IBI_clean_ms = 1000,
    GSR_US = 1
  )

  expect_error(
    export_gazepoint_rhrv_input(dat, ibi_col = "missing"),
    "`ibi_col`"
  )

  expect_error(
    prepare_gazepoint_neurokit_eda_input(dat, eda_col = "missing"),
    "`eda_col`"
  )

  expect_error(
    run_gazepoint_neurokit_eda_crosscheck(dat, execute = NA),
    "`execute` must be TRUE or FALSE"
  )
})
