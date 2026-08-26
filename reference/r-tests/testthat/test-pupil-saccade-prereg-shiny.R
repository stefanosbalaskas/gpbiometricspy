test_that("baseline_correct_gazepoint_pupil applies subtractive correction", {
  dat <- data.frame(
    participant = "p1",
    trial = 1,
    time = c(-240, -220, -200, 0, 100, 200),
    pupil = c(3, 3.2, 3.4, 4, 4.2, 4.4)
  )

  out <- baseline_correct_gazepoint_pupil(
    dat,
    pupil_col = "pupil",
    time_col = "time",
    trial_cols = c("participant", "trial"),
    baseline_window = c(-240, -200)
  )

  expect_true("pupil_baseline_corrected" %in% names(out))
  expect_equal(out$pupil_baseline_corrected[4], 4 - 3.2, tolerance = 1e-10)

  summary <- attr(out, "pupil_baseline_summary")
  expect_equal(summary$status, "pupil_baseline_correction_complete")
})

test_that("plot_gazepoint_saccade_main_sequence returns plotted data invisibly", {
  dat <- data.frame(
    amplitude_deg = c(1, 2, 3, 4, 5),
    peak_velocity_deg_s = c(100, 180, 250, 300, 340)
  )

  out <- plot_gazepoint_saccade_main_sequence(
    dat,
    amplitude_col = "amplitude_deg",
    peak_velocity_col = "peak_velocity_deg_s",
    add_smoother = FALSE
  )

  expect_true(is.list(out))
  expect_equal(nrow(out$data), 5)
})

test_that("create_gazepoint_preregistration_template returns cautious text", {
  txt <- create_gazepoint_preregistration_template(
    study_title = "Test study",
    signal_standardization = "within_participant_z",
    artifact_rules = "kleckner_style"
  )

  expect_true(grepl("Test study", txt))
  expect_true(grepl("z =", txt, fixed = TRUE))
  expect_true(grepl("Kleckner-style", txt))
  expect_true(grepl("does not", txt) || grepl("will not", txt))
})

test_that("run_gpbiometrics_shiny errors clearly without shiny or returns app", {
  if (!requireNamespace("shiny", quietly = TRUE)) {
    expect_error(run_gpbiometrics_shiny(), "shiny")
  } else {
    app <- run_gpbiometrics_shiny()
    expect_true(inherits(app, "shiny.appobj"))
  }
})
