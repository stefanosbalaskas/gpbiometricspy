test_that("summarise_gazepoint_gsr_windows summarises grouped GSR data", {
  dat <- data.frame(
    USER = c("U1", "U1", "U2", "U2"),
    MEDIA_ID = c(1, 1, 1, 1),
    GSR_US = c(2.0, 2.4, 1.0, 1.2),
    GSRV = c(1, 1, 1, 1)
  )

  out <- summarise_gazepoint_gsr_windows(
    dat,
    group_columns = c("USER", "MEDIA_ID")
  )

  expect_equal(nrow(out), 2)
  expect_true("mean_value" %in% names(out))

  u1 <- out[out$USER == "U1", ]

  expect_equal(u1$usable_rows, 2)
  expect_equal(u1$mean_value, 2.2, tolerance = 1e-8)
  expect_equal(u1$change_value, 0.4, tolerance = 1e-8)
})


test_that("summarise_gazepoint_hr_windows excludes invalid and zero values", {
  dat <- data.frame(
    USER = c("U1", "U1", "U1", "U1"),
    HR = c(70, 72, 0, 90),
    HRV = c(1, 1, 0, 0)
  )

  out <- summarise_gazepoint_hr_windows(
    dat,
    group_columns = "USER"
  )

  expect_equal(out$usable_rows, 2)
  expect_equal(out$mean_value, 71, tolerance = 1e-8)
  expect_equal(out$zero_rows, 1)
})


test_that("summarise_gazepoint_engagement_windows keeps valid zero dial values", {
  dat <- data.frame(
    USER = c("U1", "U1", "U1"),
    DIAL = c(0, 0.5, 1),
    DIALV = c(1, 1, 1)
  )

  out <- summarise_gazepoint_engagement_windows(
    dat,
    group_columns = "USER"
  )

  expect_equal(out$usable_rows, 3)
  expect_equal(out$mean_value, 0.5, tolerance = 1e-8)
})


test_that("summarise_gazepoint_signal_windows supports ungrouped summaries", {
  dat <- data.frame(
    GSR_US = c(2.0, 2.2, 2.4),
    GSRV = c(1, 1, 1)
  )

  out <- summarise_gazepoint_gsr_windows(dat)

  expect_equal(nrow(out), 1)
  expect_equal(out$window, "all")
  expect_equal(out$mean_value, 2.2, tolerance = 1e-8)
})


test_that("summarise_gazepoint_multimodal_windows combines signal summaries", {
  dat <- data.frame(
    USER = c("U1", "U1", "U2", "U2"),
    MEDIA_ID = c(1, 1, 1, 1),
    GSR_US = c(2.0, 2.4, 1.0, 1.2),
    GSRV = c(1, 1, 1, 1),
    HR = c(70, 72, 80, 82),
    HRV = c(1, 1, 1, 1),
    DIAL = c(0.1, 0.2, 0.3, 0.4),
    DIALV = c(1, 1, 1, 1)
  )

  out <- summarise_gazepoint_multimodal_windows(
    dat,
    group_columns = c("USER", "MEDIA_ID")
  )

  expect_equal(nrow(out), 2)
  expect_true("gsr_mean_value" %in% names(out))
  expect_true("hr_mean_value" %in% names(out))
  expect_true("dial_mean_value" %in% names(out))

  u1 <- out[out$USER == "U1", ]

  expect_equal(u1$gsr_mean_value, 2.2, tolerance = 1e-8)
  expect_equal(u1$hr_mean_value, 71, tolerance = 1e-8)
  expect_equal(u1$dial_mean_value, 0.15, tolerance = 1e-8)
})


test_that("window summaries reject missing grouping columns", {
  dat <- data.frame(
    GSR_US = c(2.0, 2.2),
    GSRV = c(1, 1)
  )

  expect_error(
    summarise_gazepoint_gsr_windows(dat, group_columns = "USER"),
    "group_columns"
  )
})
