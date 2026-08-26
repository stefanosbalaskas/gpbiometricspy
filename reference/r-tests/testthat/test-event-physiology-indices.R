
test_that("epoch_gazepoint_scr returns event-level SCR metrics", {
  time <- seq(0, 10, by = 0.1)
  gsr <- rep(0, length(time))
  gsr <- gsr + exp(-((time - 5.8)^2) / 0.02) * 0.5
  gsr <- gsr + exp(-((time - 7.0)^2) / 0.03) * 0.3

  dat <- data.frame(time_s = time, GSR = gsr)

  out <- epoch_gazepoint_scr(
    data = dat,
    events = 5,
    pre = 1,
    post = 3,
    min_amplitude = 0.05,
    min_distance_s = 0.5
  )

  expect_true(is.data.frame(out))
  expect_equal(nrow(out), 1)
  expect_true(out$scr_count >= 1)
  expect_true(out$scr_max_amplitude > 0.1)
  expect_true(out$n_samples > 0)
})

test_that("epoch_gazepoint_scr carries event metadata", {
  time <- seq(0, 8, by = 0.1)
  gsr <- exp(-((time - 3.5)^2) / 0.02)

  dat <- data.frame(time_s = time, EDA = gsr)
  events <- data.frame(
    trial = "T1",
    condition = "A",
    onset = 3
  )

  out <- epoch_gazepoint_scr(
    dat,
    events = events,
    pre = 1,
    post = 2,
    signal_col = "EDA",
    event_time_col = "onset",
    event_id_col = "trial",
    event_group_cols = "condition",
    min_amplitude = 0.05
  )

  expect_equal(out$event_id, "T1")
  expect_equal(out$condition, "A")
  expect_true(out$scr_count >= 1)
})

test_that("normalize_gazepoint_scr supports vector methods", {
  x <- c(1, 2, 3)

  expect_equal(normalize_gazepoint_scr(x, method = "percent_max"), c(100 / 3, 200 / 3, 100))
  expect_equal(normalize_gazepoint_scr(x, method = "range"), c(0, 0.5, 1))
  expect_equal(round(mean(normalize_gazepoint_scr(x, method = "z")), 10), 0)
})

test_that("normalize_gazepoint_scr supports grouped data frames", {
  dat <- data.frame(
    participant = c("P01", "P01", "P02", "P02"),
    scr_amplitude = c(1, 2, 10, 20)
  )

  out <- normalize_gazepoint_scr(
    dat,
    method = "percent_max",
    group_cols = "participant"
  )

  expect_true("scr_amplitude_normalized" %in% names(out))
  expect_equal(out$scr_amplitude_normalized, c(50, 100, 50, 100))
})

test_that("flag_gazepoint_rr_outliers flags implausible intervals", {
  rr <- c(800, 810, 790, 2500, 805, 100)

  flags <- flag_gazepoint_rr_outliers(rr, method = "range", min_rr = 300, max_rr = 2000)

  expect_equal(flags, c(FALSE, FALSE, FALSE, TRUE, FALSE, TRUE))
})

test_that("flag_gazepoint_rr_outliers can return filtered vector and data", {
  rr <- c(800, 810, 790, 2500)

  filtered <- flag_gazepoint_rr_outliers(rr, method = "range", return = "filtered")
  detail <- flag_gazepoint_rr_outliers(rr, method = "range", return = "data")

  expect_true(is.na(filtered[4]))
  expect_true(is.data.frame(detail))
  expect_true(detail$is_outlier[4])
  expect_equal(detail$rr_filtered[1], 800)
})

test_that("flag_gazepoint_rr_outliers supports robust MAD rule", {
  rr <- c(800, 805, 810, 795, 1600)

  flags <- flag_gazepoint_rr_outliers(
    rr,
    method = "mad",
    mad_threshold = 3,
    min_rr = 300,
    max_rr = 2000
  )

  expect_true(flags[5])
})

test_that("compute_gazepoint_engagement_index summarizes a dial vector", {
  dial <- c(20, 60, 80, 40)
  time <- c(0, 1, 2, 3)

  out <- compute_gazepoint_engagement_index(dial, time = time, threshold = 50)

  expect_true(is.data.frame(out))
  expect_equal(out$n_valid, 4)
  expect_equal(out$mean_engagement, 50)
  expect_equal(out$duration_s, 3)
  expect_true(out$percent_time_above_threshold > 0)
})

test_that("compute_gazepoint_engagement_index supports scalar output", {
  dial <- c(20, 60, 80)
  time <- c(0, 1, 2)

  out <- compute_gazepoint_engagement_index(
    dial,
    time = time,
    threshold = 50,
    return = "scalar"
  )

  expect_true(is.numeric(out))
  expect_length(out, 1)
})

test_that("compute_gazepoint_engagement_index supports grouping", {
  dial <- c(20, 60, 80, 10, 90, 100)
  time <- c(0, 1, 2, 0, 1, 2)
  group <- c("A", "A", "A", "B", "B", "B")

  out <- compute_gazepoint_engagement_index(
    dial,
    time = time,
    threshold = 50,
    group = group
  )

  expect_equal(nrow(out), 2)
  expect_true(all(c("A", "B") %in% out$group))
  expect_true(all(out$n_valid == 3))
})

