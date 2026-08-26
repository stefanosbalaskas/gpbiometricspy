test_that("extract_gazepoint_ttl_events extracts TTL changes", {
  dat <- data.frame(
    source_participant = c("User 1", "User 1", "User 1", "User 1"),
    MEDIA_ID = c(0, 0, 0, 0),
    CNT = c(1, 2, 3, 4),
    TTL0 = c(1007, 1007, 1008, 1008),
    TTLV = c(1, 1, 1, 1)
  )

  out <- extract_gazepoint_ttl_events(
    dat,
    group_columns = c("source_participant", "MEDIA_ID")
  )

  expect_equal(nrow(out), 2)
  expect_equal(out$ttl_channel, c("TTL0", "TTL0"))
  expect_equal(out$ttl_value, c(1007, 1008))
  expect_equal(out$CNT, c(1, 3))
  expect_equal(out$ttl_validity, c(1, 1))
})


test_that("extract_gazepoint_ttl_events can omit initial TTL values", {
  dat <- data.frame(
    CNT = c(1, 2, 3, 4),
    TTL0 = c(1007, 1007, 1008, 1008),
    TTLV = c(1, 1, 1, 1)
  )

  out <- extract_gazepoint_ttl_events(
    dat,
    include_initial = FALSE
  )

  expect_equal(nrow(out), 1)
  expect_equal(out$ttl_value, 1008)
  expect_equal(out$previous_ttl_value, 1007)
})


test_that("extract_gazepoint_ttl_events supports nonzero mode", {
  dat <- data.frame(
    CNT = c(1, 2, 3, 4),
    TTL0 = c(0, 1007, 0, 1008),
    TTLV = c(1, 1, 1, 1)
  )

  out <- extract_gazepoint_ttl_events(
    dat,
    mode = "nonzero"
  )

  expect_equal(nrow(out), 2)
  expect_equal(out$ttl_value, c(1007, 1008))
  expect_equal(out$CNT, c(2, 4))
})


test_that("extract_gazepoint_ttl_events separates groups", {
  dat <- data.frame(
    source_participant = c("User 1", "User 1", "User 2", "User 2"),
    CNT = c(1, 2, 1, 2),
    TTL0 = c(1007, 1008, 1007, 1008),
    TTLV = c(1, 1, 1, 1)
  )

  out <- extract_gazepoint_ttl_events(
    dat,
    group_columns = "source_participant",
    include_initial = FALSE
  )

  expect_equal(nrow(out), 2)
  expect_true(all(c("User 1", "User 2") %in% out$source_participant))
  expect_equal(out$ttl_value, c(1008, 1008))
})


test_that("extract_gazepoint_ttl_events filters invalid TTL rows by default", {
  dat <- data.frame(
    CNT = c(1, 2, 3, 4),
    TTL0 = c(1007, 1008, 1009, 1010),
    TTLV = c(0, 0, 1, 1)
  )

  out <- extract_gazepoint_ttl_events(dat)

  expect_equal(nrow(out), 2)
  expect_equal(out$ttl_value, c(1009, 1010))
  expect_equal(out$ttl_validity, c(1, 1))
})


test_that("extract_gazepoint_ttl_events can include invalid TTL rows when requested", {
  dat <- data.frame(
    CNT = c(1, 2, 3, 4),
    TTL0 = c(1007, 1008, 1009, 1010),
    TTLV = c(0, 0, 1, 1)
  )

  out <- extract_gazepoint_ttl_events(
    dat,
    require_validity = FALSE
  )

  expect_equal(nrow(out), 4)
  expect_equal(out$ttl_value, c(1007, 1008, 1009, 1010))
})


test_that("extract_gazepoint_ttl_events rejects missing TTL columns", {
  dat <- data.frame(
    CNT = c(1, 2),
    GSR_US = c(1.1, 1.2)
  )

  expect_error(
    extract_gazepoint_ttl_events(dat),
    "No TTL columns"
  )
})


test_that("extract_gazepoint_ttl_events returns empty table when no events exist", {
  dat <- data.frame(
    source_participant = c("User 1", "User 1"),
    CNT = c(1, 2),
    TTL0 = c(0, 0),
    TTLV = c(1, 1)
  )

  out <- extract_gazepoint_ttl_events(
    dat,
    group_columns = "source_participant",
    mode = "nonzero"
  )

  expect_true(is.data.frame(out))
  expect_equal(nrow(out), 0)
  expect_true("source_participant" %in% names(out))
  expect_true("ttl_channel" %in% names(out))
})
