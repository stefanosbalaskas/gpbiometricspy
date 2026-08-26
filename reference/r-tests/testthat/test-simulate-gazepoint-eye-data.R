
test_that("simulate_gazepoint_eye_data returns Gazepoint-style columns", {
  dat <- simulate_gazepoint_eye_data(list(n = 120, seed = 1))

  expect_true(is.data.frame(dat))
  expect_equal(nrow(dat), 120)
  expect_true(all(c(
    "time_s", "MSTIMER", "BPOGX", "BPOGY", "FPOGX", "FPOGY",
    "LPD", "RPD", "LPV", "RPV", "fixation_id", "in_blink"
  ) %in% names(dat)))
  expect_true(all(dat$BPOGX >= 0 & dat$BPOGX <= 1))
  expect_true(all(dat$BPOGY >= 0 & dat$BPOGY <= 1))
})

test_that("simulate_gazepoint_eye_data is deterministic with seed", {
  a <- simulate_gazepoint_eye_data(list(n = 80, seed = 42))
  b <- simulate_gazepoint_eye_data(list(n = 80, seed = 42))

  expect_equal(a$BPOGX, b$BPOGX)
  expect_equal(a$BPOGY, b$BPOGY)
  expect_equal(a$LPD, b$LPD)
  expect_equal(a$in_blink, b$in_blink)
})

test_that("simulate_gazepoint_eye_data supports duration and sampling rate", {
  dat <- simulate_gazepoint_eye_data(list(
    duration_s = 2,
    sampling_rate_hz = 50,
    seed = 3
  ))

  expect_equal(nrow(dat), 100)
  expect_equal(attr(dat, "sampling_rate_hz"), 50)
  expect_equal(max(dat$MSTIMER), 1980)
})

test_that("simulate_gazepoint_eye_data can generate blink-heavy data", {
  dat <- simulate_gazepoint_eye_data(list(
    n = 600,
    sampling_rate_hz = 60,
    blink_rate_per_min = 120,
    blink_duration_mean_s = 0.10,
    blink_duration_sd_s = 0.01,
    seed = 10
  ))

  expect_true(any(dat$in_blink))
  expect_true(any(is.na(dat$LPD)))
  expect_true(any(dat$LPV == 0))
})

test_that("simulate_gazepoint_eye_data can generate invalid gaze samples", {
  dat <- simulate_gazepoint_eye_data(list(
    n = 200,
    seed = 12,
    include_invalid_gaze = TRUE,
    invalid_gaze_prop = 0.10
  ))

  expect_true(any(!dat$gaze_valid_simulated))
  expect_true(any(dat$BPOGX > 1))
})

test_that("simulate_gazepoint_eye_data works with pupil and gaze helpers", {
  dat <- simulate_gazepoint_eye_data(list(
    n = 500,
    sampling_rate_hz = 60,
    blink_rate_per_min = 120,
    seed = 123
  ))

  blinks <- detect_gazepoint_pupil_blinks(
    dat,
    pupil_cols = c("LPD", "RPD"),
    time_col = "time_s"
  )

  cleaned <- clean_gazepoint_pupil_signal(
    dat,
    pupil_cols = "LPD",
    time_col = "time_s"
  )

  fix_summary <- summarize_gazepoint_fixations(
    data.frame(
      trial = dat$trial,
      AOI = "screen",
      FPOGD = rep(1 / 60, nrow(dat)),
      FPOGX = dat$FPOGX,
      FPOGY = dat$FPOGY
    ),
    group_cols = c("trial", "AOI")
  )

  expect_true(is.data.frame(blinks))
  expect_true("LPD_clean" %in% names(cleaned))
  expect_true(is.data.frame(fix_summary))
  expect_true(fix_summary$n_fixations > 0)
})

