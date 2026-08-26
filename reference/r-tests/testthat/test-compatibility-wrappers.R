test_that("summarise_gazepoint_dial_windows validates data input", {
  expect_error(
    summarise_gazepoint_dial_windows(1:3),
    "`data` must be"
  )
})


test_that("summarise_gazepoint_dial_windows validates explicit dial column", {
  df <- data.frame(
    DIAL = c(40, 45, 50)
  )

  expect_error(
    summarise_gazepoint_dial_windows(df, dial_col = "missing"),
    "not found"
  )
})


test_that("summarise_gazepoint_dial_windows delegates to engagement-window helper", {
  df <- data.frame(
    USER = rep(c("P1", "P2"), each = 3),
    DIAL = c(40, 45, 50, 55, 60, 65)
  )

  direct <- summarise_gazepoint_engagement_windows(df)
  alias <- summarise_gazepoint_dial_windows(df)

  expect_equal(alias, direct)
})


test_that("summarise_gazepoint_dial_windows supports explicit dial_col alias", {
  df <- data.frame(
    USER = rep(c("P1", "P2"), each = 3),
    dial_value = c(40, 45, 50, 55, 60, 65)
  )

  direct <- summarise_gazepoint_engagement_windows(
    df,
    value_column = "dial_value"
  )

  alias <- summarise_gazepoint_dial_windows(
    df,
    dial_col = "dial_value"
  )

  expect_equal(alias, direct)
})


test_that("join_gazepoint_biometrics_to_gp3tools validates biometric input", {
  master <- data.frame(USER = "P1", CNT = 1)

  expect_error(
    join_gazepoint_biometrics_to_gp3tools(1:3, master),
    "`biometrics` must be"
  )
})


test_that("join_gazepoint_biometrics_to_gp3tools validates gp3tools master input", {
  biometrics <- data.frame(USER = "P1", CNT = 1)

  expect_error(
    join_gazepoint_biometrics_to_gp3tools(biometrics, 1:3),
    "`gp3tools_master` must be"
  )
})


test_that("join_gazepoint_biometrics_to_gp3tools delegates to master-join helper", {
  biometrics <- data.frame(
    USER = rep("P1", 3),
    CNT = 1:3,
    HR = c(70, 71, 72)
  )

  master <- data.frame(
    USER = rep("P1", 3),
    CNT = 1:3,
    AOI = c("A", "B", "A")
  )

  direct <- join_gazepoint_biometrics_to_master(
    biometrics,
    master,
    by = c("USER", "CNT")
  )

  alias <- join_gazepoint_biometrics_to_gp3tools(
    biometrics,
    master,
    by = c("USER", "CNT")
  )

  expect_equal(alias, direct)
})


test_that("compatibility wrappers expose stable formal arguments", {
  expect_true("data" %in% names(formals(summarise_gazepoint_dial_windows)))
  expect_true("dial_col" %in% names(formals(summarise_gazepoint_dial_windows)))

  expect_true("biometrics" %in% names(formals(join_gazepoint_biometrics_to_gp3tools)))
  expect_true("gp3tools_master" %in% names(formals(join_gazepoint_biometrics_to_gp3tools)))
})
