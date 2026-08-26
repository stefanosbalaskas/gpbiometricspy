
test_that("import_gazepoint_data imports session-prefixed CSV files", {
  tmp <- tempfile("gp_import_")
  dir.create(tmp)

  write.csv(
    data.frame(time_s = 1:3, GSR = c(1, 2, 3)),
    file.path(tmp, "S01_biometrics.csv"),
    row.names = FALSE
  )

  write.csv(
    data.frame(time_s = 1:3, FPOGX = c(.1, .2, .3), FPOGY = c(.4, .5, .6)),
    file.path(tmp, "S01_all_gaze.csv"),
    row.names = FALSE
  )

  write.csv(
    data.frame(time_s = 1:3, GSR = c(4, 5, 6)),
    file.path(tmp, "S02_biometrics.csv"),
    row.names = FALSE
  )

  out <- import_gazepoint_data(tmp, session = "S01")

  expect_true(inherits(out, "gazepoint_session_data"))
  expect_equal(length(out), 2)
  expect_true(all(vapply(out, is.data.frame, logical(1))))
  expect_true(all(c("gp_source_file", "gp_source_basename", "gp_source_index") %in% names(out[[1]])))

  index <- attr(out, "file_index")
  expect_true(is.data.frame(index))
  expect_equal(nrow(index), 2)
  expect_true(all(index$rows == 3))
  expect_true(all(index$detected_type %in% c("biometrics", "all_gaze")))
})

test_that("import_gazepoint_data reads semicolon-delimited files", {
  tmp <- tempfile("gp_import_semicolon_")
  dir.create(tmp)

  writeLines(
    c("time_s;PPG", "0;1.1", "1;1.2"),
    file.path(tmp, "S03_biometrics.csv")
  )

  out <- import_gazepoint_data(tmp, session = "S03")

  expect_equal(length(out), 1)
  expect_true(all(c("time_s", "PPG") %in% names(out[[1]])))
  expect_equal(nrow(out[[1]]), 2)
})

test_that("import_gazepoint_data errors clearly when folder or files are missing", {
  expect_error(
    import_gazepoint_data(file.path(tempdir(), "folder_that_does_not_exist")),
    "Folder does not exist"
  )

  tmp <- tempfile("gp_import_empty_")
  dir.create(tmp)

  expect_error(
    import_gazepoint_data(tmp),
    "No files matching"
  )
})

test_that("impute_gazepoint_missing linearly imputes numeric vectors", {
  x <- c(1, NA, 3, 4)

  y <- impute_gazepoint_missing(x, method = "linear")

  expect_equal(y, c(1, 2, 3, 4))
  expect_false(anyNA(y))
})

test_that("impute_gazepoint_missing respects max_gap", {
  x <- c(1, NA, NA, 4, NA, 6)

  y <- impute_gazepoint_missing(x, method = "linear", max_gap = 1)

  expect_true(is.na(y[2]))
  expect_true(is.na(y[3]))
  expect_false(is.na(y[5]))
})

test_that("impute_gazepoint_missing imputes selected data-frame columns", {
  dat <- data.frame(
    time_s = 1:5,
    GSR = c(1, NA, 3, NA, 5),
    label = letters[1:5]
  )

  out <- impute_gazepoint_missing(
    dat,
    method = "linear",
    cols = "GSR",
    time_col = "time_s"
  )

  expect_true(is.data.frame(out))
  expect_false(anyNA(out$GSR))
  expect_true("GSR_was_imputed" %in% names(out))
  expect_equal(sum(out$GSR_was_imputed), 2)

  summary <- attr(out, "imputation_summary")
  expect_true(is.data.frame(summary))
  expect_equal(summary$n_missing_before, 2)
  expect_equal(summary$n_missing_after, 0)
})

test_that("impute_gazepoint_missing imputes within groups only", {
  dat <- data.frame(
    participant = c("P01", "P01", "P01", "P02", "P02", "P02"),
    time_s = c(1, 2, 3, 1, 2, 3),
    PPG = c(1, NA, 3, 10, NA, 14)
  )

  out <- impute_gazepoint_missing(
    dat,
    method = "linear",
    cols = "PPG",
    time_col = "time_s",
    group_cols = "participant"
  )

  expect_equal(out$PPG, c(1, 2, 3, 10, 12, 14))
  expect_equal(sum(out$PPG_was_imputed), 2)
})

test_that("impute_gazepoint_missing supports ts input", {
  x <- stats::ts(c(1, NA, 3), start = 1, frequency = 10)

  y <- impute_gazepoint_missing(x)

  expect_true(is.ts(y))
  expect_equal(as.numeric(y), c(1, 2, 3))
  expect_equal(stats::frequency(y), 10)
})

