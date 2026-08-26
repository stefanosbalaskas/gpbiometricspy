#' Plot an SCR specification curve
#'
#' Plots a specification-curve style display from the output of
#' `run_gazepoint_scr_multiverse()` or from a compatible data frame.
#'
#' @param x Output from `run_gazepoint_scr_multiverse()` or a data frame.
#' @param estimate_col Column to rank and plot. Defaults to
#'   `"mean_response_amplitude"` when available, otherwise `"response_rate"`.
#' @param specification_col Specification identifier column.
#' @param add_zero_line Logical. If `TRUE`, draw a horizontal zero line.
#' @param main Plot title.
#'
#' @return Invisibly returns a list with plot data and settings.
#' @export
plot_gazepoint_scr_specification_curve <- function(x,
                                                   estimate_col = NULL,
                                                   specification_col = "specification_id",
                                                   add_zero_line = TRUE,
                                                   main = "SCR specification curve") {
  if (inherits(x, "gazepoint_scr_multiverse")) {
    dat <- x$specification_summary
  } else if (is.data.frame(x)) {
    dat <- x
  } else {
    stop(
      "`x` must be output from `run_gazepoint_scr_multiverse()` or a data frame.",
      call. = FALSE
    )
  }

  if (!is.data.frame(dat) || nrow(dat) == 0) {
    stop("No specification-summary data available to plot.", call. = FALSE)
  }

  if (is.null(estimate_col)) {
    estimate_col <- if ("mean_response_amplitude" %in% names(dat)) {
      "mean_response_amplitude"
    } else if ("response_rate" %in% names(dat)) {
      "response_rate"
    } else {
      stop(
        "Could not infer `estimate_col`; supply it explicitly.",
        call. = FALSE
      )
    }
  }

  if (!estimate_col %in% names(dat)) {
    stop("Column `", estimate_col, "` was not found.", call. = FALSE)
  }

  if (!specification_col %in% names(dat)) {
    stop("Column `", specification_col, "` was not found.", call. = FALSE)
  }

  plot_data <- dat[is.finite(dat[[estimate_col]]), , drop = FALSE]

  if (nrow(plot_data) == 0) {
    stop("No finite estimates available to plot.", call. = FALSE)
  }

  plot_data <- plot_data[order(plot_data[[estimate_col]]), , drop = FALSE]
  plot_data$specification_rank <- seq_len(nrow(plot_data))

  graphics::plot(
    plot_data$specification_rank,
    plot_data[[estimate_col]],
    type = "b",
    xlab = "Specification rank",
    ylab = estimate_col,
    main = main
  )

  if (isTRUE(add_zero_line)) {
    graphics::abline(h = 0, lty = 2)
  }

  invisible(
    structure(
      list(
        plot_data = plot_data,
        settings = list(
          estimate_col = estimate_col,
          specification_col = specification_col,
          add_zero_line = add_zero_line,
          main = main
        ),
        interpretation = paste(
          "The specification curve ranks estimates across defensible SCR scoring specifications.",
          "It supports sensitivity reporting and does not identify a universally correct specification."
        )
      ),
      class = c("gazepoint_scr_specification_curve_plot", "list")
    )
  )
}
