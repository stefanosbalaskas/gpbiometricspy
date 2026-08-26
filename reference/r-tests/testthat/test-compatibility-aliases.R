test_that("prepare_gazepoint_rhrv_input wraps export_gazepoint_rhrv_input", {
  dat <- data.frame(
    participant = c("p1", "p1", "p1", "p2", "p2", "p2"),
    IBI_clean_ms = c(800, 810, 790, 900, 890, 910)
  )

  old <- export_gazepoint_rhrv_input(
    dat,
    ibi_col = "IBI_clean_ms",
    group_cols = "participant"
  )

  new <- prepare_gazepoint_rhrv_input(
    dat,
    ibi_col = "IBI_clean_ms",
    group_cols = "participant"
  )

  expect_named(new, names(old))
  expect_equal(new$overview, old$overview)
  expect_equal(new$beat_table, old$beat_table)
  expect_equal(new$group_summary, old$group_summary)
  expect_equal(new$settings$ibi_col, "IBI_clean_ms")
})

test_that("prepare_gazepoint_rhrv_input preserves conservative IBI filtering", {
  dat <- data.frame(
    participant = "p1",
    IBI_clean_ms = c(250, 800, 1000, 2500)
  )

  out <- prepare_gazepoint_rhrv_input(
    dat,
    ibi_col = "IBI_clean_ms",
    group_cols = "participant",
    min_ibi_ms = 300,
    max_ibi_ms = 2000
  )

  expect_true(all(out$beat_table$ibi_ms >= 300))
  expect_true(all(out$beat_table$ibi_ms <= 2000))
  expect_equal(nrow(out$beat_table), 2)
})

test_that("standardize_gazepoint_plot_contracts handles one plot", {
  skip_if_not_installed("ggplot2")

  dat <- data.frame(x = 1:3, y = c(2, 4, 6))

  p <- ggplot2::ggplot(dat, ggplot2::aes(x = x, y = y)) +
    ggplot2::geom_point()

  out <- standardize_gazepoint_plot_contracts(
    plot = p,
    plot_data = dat,
    settings = list(plot_type = "single_alias_test"),
    interpretation_notes = "Compatibility alias test.",
    plot_type = "single_alias_test"
  )

  expect_s3_class(out, "gazepoint_plot")
  expect_true(isTRUE(attr(out, "gazepoint_plot_contract")))
  expect_equal(attr(out, "plot_type"), "single_alias_test")
  expect_equal(attr(out, "plot_data"), dat)
  expect_equal(attr(out, "interpretation_notes"), "Compatibility alias test.")
})

test_that("standardize_gazepoint_plot_contracts handles a list of plots", {
  skip_if_not_installed("ggplot2")

  dat1 <- data.frame(x = 1:3, y = c(2, 4, 6))
  dat2 <- data.frame(x = 1:3, y = c(3, 6, 9))

  p1 <- ggplot2::ggplot(dat1, ggplot2::aes(x = x, y = y)) +
    ggplot2::geom_point()

  p2 <- ggplot2::ggplot(dat2, ggplot2::aes(x = x, y = y)) +
    ggplot2::geom_line()

  out <- standardize_gazepoint_plot_contracts(
    plot = list(first = p1, second = p2),
    plot_data = list(dat1, dat2),
    settings = list(
      list(plot_type = "first_alias_test"),
      list(plot_type = "second_alias_test")
    ),
    interpretation_notes = c("First plot note.", "Second plot note."),
    plot_type = c("first_alias_test", "second_alias_test")
  )

  expect_type(out, "list")
  expect_length(out, 2)
  expect_named(out, c("first", "second"))

  expect_true(all(vapply(
    out,
    function(x) isTRUE(attr(x, "gazepoint_plot_contract")),
    logical(1)
  )))

  expect_equal(attr(out$first, "plot_type"), "first_alias_test")
  expect_equal(attr(out$second, "plot_type"), "second_alias_test")
  expect_equal(attr(out$first, "plot_data"), dat1)
  expect_equal(attr(out$second, "plot_data"), dat2)
})

test_that("prepare_gazepoint_rhrv_input handles groups with no valid IBI intervals", {
  dat <- data.frame(
    participant = c("p1", "p1", "p2", "p2"),
    IBI_clean_ms = c(800, 810, NA_real_, 2500)
  )

  out <- prepare_gazepoint_rhrv_input(
    dat,
    ibi_col = "IBI_clean_ms",
    group_cols = "participant",
    min_ibi_ms = 300,
    max_ibi_ms = 2000
  )

  expect_s3_class(out, "gazepoint_rhrv_input_export")
  expect_true(is.data.frame(out$beat_table))
  expect_true(is.data.frame(out$group_summary))
  expect_true(is.data.frame(out$manifest))
  expect_true(is.list(out$settings))

  expect_equal(out$settings$ibi_col, "IBI_clean_ms")
  expect_true(all(out$beat_table$ibi_ms >= 300))
  expect_true(all(out$beat_table$ibi_ms <= 2000))

  # The second group has no valid IBI values after filtering.
  # The important regression is that this no longer errors and that no invalid
  # intervals are emitted into the beat table.
  expect_false(any(is.na(out$beat_table$ibi_ms)))
  expect_false(any(out$beat_table$ibi_ms > 2000))
  expect_false(any(out$beat_table$ibi_ms < 300))

  # At least the valid participant should remain represented in exported beats.
  expect_true(any(out$beat_table$group_id == "p1"))
  expect_false(any(out$beat_table$group_id == "p2"))
})
