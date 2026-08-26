test_that("standardize_gazepoint_biometrics_within_unit standardizes within participant", {
  dat <- data.frame(
    participant = rep(c("p1", "p2"), each = 5),
    GSR_US = c(1, 2, 3, 4, 5, 10, 20, 30, 40, 50),
    HR = c(70, 71, 72, 73, 74, 80, 82, 84, 86, 88)
  )

  out <- standardize_gazepoint_biometrics_within_unit(
    dat,
    signal_cols = c("GSR_US", "HR"),
    unit_cols = "participant"
  )

  expect_s3_class(out, "gazepoint_within_unit_standardized")
  expect_true(all(c("GSR_US_z_within", "HR_z_within") %in% names(out)))

  by_participant <- split(out, out$participant)

  expect_equal(mean(by_participant$p1$GSR_US_z_within), 0, tolerance = 1e-10)
  expect_equal(stats::sd(by_participant$p1$GSR_US_z_within), 1, tolerance = 1e-10)
  expect_equal(mean(by_participant$p2$GSR_US_z_within), 0, tolerance = 1e-10)
  expect_equal(stats::sd(by_participant$p2$GSR_US_z_within), 1, tolerance = 1e-10)

  summary <- attr(out, "standardization_summary")
  parameters <- attr(out, "standardization_parameters")

  expect_equal(summary$status, "within_unit_standardization_complete")
  expect_equal(summary$unit_count, 2)
  expect_equal(summary$signal_count, 2)
  expect_true(is.data.frame(parameters))
  expect_equal(nrow(parameters), 4)
})

test_that("standardize_gazepoint_biometrics_within_unit uses reference rows when supplied", {
  dat <- data.frame(
    participant = rep(c("p1", "p2"), each = 6),
    baseline = rep(c(TRUE, TRUE, TRUE, FALSE, FALSE, FALSE), 2),
    GSR_US = c(1, 2, 3, 4, 5, 6, 10, 20, 30, 40, 50, 60)
  )

  out <- standardize_gazepoint_biometrics_within_unit(
    dat,
    signal_cols = "GSR_US",
    unit_cols = "participant",
    reference_col = "baseline",
    reference_value = TRUE
  )

  baseline_rows <- out$baseline

  p1_base <- out$participant == "p1" & baseline_rows
  p2_base <- out$participant == "p2" & baseline_rows

  expect_equal(mean(out$GSR_US_z_within[p1_base]), 0, tolerance = 1e-10)
  expect_equal(stats::sd(out$GSR_US_z_within[p1_base]), 1, tolerance = 1e-10)
  expect_equal(mean(out$GSR_US_z_within[p2_base]), 0, tolerance = 1e-10)
  expect_equal(stats::sd(out$GSR_US_z_within[p2_base]), 1, tolerance = 1e-10)

  parameters <- attr(out, "standardization_parameters")
  expect_true(all(parameters$n_reference_rows == 3))
})

test_that("standardize_gazepoint_biometrics_within_unit handles zero standard deviation conservatively", {
  dat <- data.frame(
    participant = rep(c("p1", "p2"), each = 4),
    GSR_US = c(1, 1, 1, 1, 1, 2, 3, 4)
  )

  out_na <- standardize_gazepoint_biometrics_within_unit(
    dat,
    signal_cols = "GSR_US",
    unit_cols = "participant",
    zero_sd_action = "NA"
  )

  expect_true(all(is.na(out_na$GSR_US_z_within[out_na$participant == "p1"])))
  expect_false(all(is.na(out_na$GSR_US_z_within[out_na$participant == "p2"])))

  out_zero <- standardize_gazepoint_biometrics_within_unit(
    dat,
    signal_cols = "GSR_US",
    unit_cols = "participant",
    zero_sd_action = "zero"
  )

  expect_true(all(out_zero$GSR_US_z_within[out_zero$participant == "p1"] == 0))

  summary <- attr(out_na, "standardization_summary")
  expect_equal(summary$status, "within_unit_standardization_partial")
})

test_that("standardise_gazepoint_biometrics_within_unit is an alias", {
  dat <- data.frame(
    participant = rep(c("p1", "p2"), each = 4),
    GSR_US = c(1, 2, 3, 4, 10, 20, 30, 40)
  )

  out_us <- standardize_gazepoint_biometrics_within_unit(
    dat,
    signal_cols = "GSR_US",
    unit_cols = "participant"
  )

  out_uk <- standardise_gazepoint_biometrics_within_unit(
    dat,
    signal_cols = "GSR_US",
    unit_cols = "participant"
  )

  expect_equal(out_us$GSR_US_z_within, out_uk$GSR_US_z_within)
})

test_that("standardize_gazepoint_biometrics_within_unit protects existing columns", {
  dat <- data.frame(
    participant = "p1",
    GSR_US = 1:4,
    GSR_US_z_within = 1:4
  )

  expect_error(
    standardize_gazepoint_biometrics_within_unit(
      dat,
      signal_cols = "GSR_US",
      unit_cols = "participant"
    ),
    "already exist"
  )

  out <- standardize_gazepoint_biometrics_within_unit(
    dat,
    signal_cols = "GSR_US",
    unit_cols = "participant",
    overwrite = TRUE
  )

  expect_true("GSR_US_z_within" %in% names(out))
})

test_that("standardize_gazepoint_biometrics_within_unit validates inputs", {
  dat <- data.frame(
    participant = "p1",
    GSR_US = 1:4,
    label = letters[1:4]
  )

  expect_error(
    standardize_gazepoint_biometrics_within_unit(
      dat,
      signal_cols = "missing_signal"
    ),
    "missing_signal"
  )

  expect_error(
    standardize_gazepoint_biometrics_within_unit(
      dat,
      signal_cols = "label"
    ),
    "not numeric"
  )

  expect_error(
    standardize_gazepoint_biometrics_within_unit(
      dat,
      signal_cols = "GSR_US",
      unit_cols = "missing_unit"
    ),
    "missing_unit"
  )
})
