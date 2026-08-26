test_that("create_gazepoint_biometrics_checklist returns structured output", {
  dat <- data.frame(
    TIME = c(0.01, 0.02, 0.03),
    GSR_US = c(2.0, 2.1, 2.2),
    GSRV = c(1, 1, 1),
    HR = c(75, 76, 77),
    HRV = c(1, 1, 1),
    DIAL = c(0.1, 0.2, 0.3),
    DIALV = c(1, 1, 1),
    TTL0 = c(1, 1, 1),
    TTLV = c(1, 1, 1)
  )

  checklist <- create_gazepoint_biometrics_checklist(dat)

  expect_s3_class(checklist, "gazepoint_biometrics_checklist")
  expect_true(is.data.frame(checklist$overview))
  expect_true(is.data.frame(checklist$channels))
  expect_true(is.data.frame(checklist$quality))
  expect_true(is.data.frame(checklist$missingness))
  expect_true(is.data.frame(checklist$validation_issues))
  expect_true(is.data.frame(checklist$interpretation_cautions))

  expect_true(checklist$overview$active_gsr_eda)
  expect_true(checklist$overview$active_heart_rate)
  expect_true(checklist$overview$active_engagement_dial)
})


test_that("create_gazepoint_biometrics_methods_text creates cautious methods text", {
  dat <- data.frame(
    GSR_US = c(2.0, 2.1, 2.2),
    GSRV = c(1, 1, 1),
    HR = c(75, 76, 77),
    HRV = c(1, 1, 1),
    DIAL = c(0.1, 0.2, 0.3),
    DIALV = c(1, 1, 1)
  )

  checklist <- create_gazepoint_biometrics_checklist(dat)
  text <- create_gazepoint_biometrics_methods_text(checklist)

  expect_type(text, "character")
  expect_length(text, 1)
  expect_true(grepl("Gazepoint Biometrics", text))
  expect_true(grepl("GSR/EDA", text))
  expect_true(grepl("heart rate", text))
  expect_true(grepl("engagement dial", text))
  expect_true(grepl("conservatively", text))
})


test_that("create_gazepoint_biometrics_methods_text accepts data directly", {
  dat <- data.frame(
    GSR_US = c(2.0, 2.1, 2.2),
    GSRV = c(1, 1, 1)
  )

  text <- create_gazepoint_biometrics_methods_text(data = dat)

  expect_type(text, "character")
  expect_true(grepl("processed table contained", text))
})


test_that("create_gazepoint_biometrics_methods_text requires checklist or data", {
  expect_error(
    create_gazepoint_biometrics_methods_text(),
    "Either `checklist` or `data` must be supplied"
  )
})


test_that("create_gazepoint_biometrics_methods_text rejects invalid checklist", {
  expect_error(
    create_gazepoint_biometrics_methods_text(checklist = list()),
    "must be produced"
  )
})
