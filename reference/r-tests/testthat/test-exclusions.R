test_that("recommend_gazepoint_biometric_exclusions works from window summaries", {
  windows <- data.frame(
    source_participant = c("User 0", "User 0", "User 1", "User 1"),
    MEDIA_ID = c(0, 1, 0, 1),
    gsr_usable_pct = c(0, 0, 100, 100),
    hr_usable_pct = c(0, 0, 100, 90),
    dial_usable_pct = c(0, 0, 100, 100)
  )

  out <- recommend_gazepoint_biometric_exclusions(
    data = windows,
    data_is_window_summary = TRUE,
    require_gsr = TRUE,
    require_hr = TRUE,
    require_dial = FALSE
  )

  expect_s3_class(out, "gazepoint_biometric_exclusion_recommendations")
  expect_true(is.data.frame(out$overview))
  expect_true(is.data.frame(out$window_recommendations))
  expect_true(is.data.frame(out$participant_recommendations))

  expect_equal(out$overview$n_windows, 4)
  expect_equal(out$overview$exclude_windows, 2)
  expect_equal(out$overview$keep_windows, 2)

  user0 <- out$participant_recommendations[
    out$participant_recommendations$participant == "User 0",
  ]

  user1 <- out$participant_recommendations[
    out$participant_recommendations$participant == "User 1",
  ]

  expect_equal(user0$participant_recommendation, "exclude")
  expect_equal(user1$participant_recommendation, "keep")
})


test_that("recommend_gazepoint_biometric_exclusions can review optional dial coverage", {
  windows <- data.frame(
    source_participant = "User 1",
    MEDIA_ID = 0,
    gsr_usable_pct = 100,
    hr_usable_pct = 100,
    dial_usable_pct = 0
  )

  out <- recommend_gazepoint_biometric_exclusions(
    data = windows,
    data_is_window_summary = TRUE,
    require_gsr = TRUE,
    require_hr = TRUE,
    require_dial = FALSE
  )

  expect_equal(out$window_recommendations$recommendation, "review")
  expect_true(grepl("Engagement-dial", out$window_recommendations$recommendation_reason))
})


test_that("recommend_gazepoint_biometric_exclusions works from row-level data", {
  dat <- data.frame(
    source_participant = c("User 1", "User 1", "User 1"),
    MEDIA_ID = c(0, 0, 0),
    GSR_US = c(1.1, 1.2, 1.3),
    GSRV = c(1, 1, 1),
    HR = c(70, 72, 74),
    HRV = c(1, 1, 1),
    DIAL = c(1, 1, 1),
    DIALV = c(1, 1, 1)
  )

  out <- recommend_gazepoint_biometric_exclusions(
    data = dat,
    group_columns = c("source_participant", "MEDIA_ID")
  )

  expect_equal(out$overview$n_windows, 1)
  expect_equal(out$window_recommendations$recommendation, "keep")
})


test_that("recommend_gazepoint_biometric_exclusions rejects missing summary columns", {
  windows <- data.frame(
    source_participant = "User 1",
    MEDIA_ID = 0,
    gsr_usable_pct = 100
  )

  expect_error(
    recommend_gazepoint_biometric_exclusions(
      data = windows,
      data_is_window_summary = TRUE
    ),
    "Missing columns"
  )
})


test_that("recommend_gazepoint_biometric_exclusions requires group columns for row-level data", {
  dat <- data.frame(
    GSR_US = c(1.1, 1.2),
    GSRV = c(1, 1)
  )

  expect_error(
    recommend_gazepoint_biometric_exclusions(dat),
    "group_columns"
  )
})
