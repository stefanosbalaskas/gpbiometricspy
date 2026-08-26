#' Summarise Gazepoint engagement-dial windows
#'
#' Compatibility wrapper for [summarise_gazepoint_engagement_windows()]. This
#' helper uses the term "dial" for users who refer to Gazepoint engagement-dial
#' or self-reported engagement streams, while delegating the calculation to the
#' canonical engagement-window summariser.
#'
#' @param data A data frame containing Gazepoint Biometrics engagement/dial data.
#' @param ... Additional arguments passed to
#'   [summarise_gazepoint_engagement_windows()].
#' @param dial_col Optional dial/engagement column. When supplied, it is mapped
#'   to the corresponding value-column argument of the underlying helper.
#'
#' @return The output of [summarise_gazepoint_engagement_windows()].
#'
#' @examples
#' df <- data.frame(
#'   USER = rep(c("P1", "P2"), each = 3),
#'   DIAL = c(40, 45, 50, 55, 60, 65)
#' )
#' summarise_gazepoint_dial_windows(df)
#'
#' @export
summarise_gazepoint_dial_windows <- function(data, ..., dial_col = NULL) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  if (!is.null(dial_col)) {
    .gpbiom_assert_columns(data, dial_col, "dial_col")
  }

  args <- list(...)

  if (!is.null(dial_col)) {
    args <- .gpbiom_add_alias_argument(
      args = args,
      target_function = summarise_gazepoint_engagement_windows,
      aliases = c(
        "value_column",
        "engagement_col",
        "engagement_column",
        "dial_col",
        "dial_column",
        "value_col",
        "signal_col",
        "signal_column"
      ),
      value = dial_col
    )
  }

  .gpbiom_call_with_data_first(
    target_function = summarise_gazepoint_engagement_windows,
    data = data,
    args = args
  )
}


#' Join Gazepoint Biometrics data to gp3tools-style eye-tracking data
#'
#' Compatibility wrapper for [join_gazepoint_biometrics_to_master()]. This alias
#' is provided for users who work with a gp3tools master table and want an
#' explicit gp3tools-facing function name. The implementation delegates to the
#' canonical biometric-to-master join helper.
#'
#' @param biometrics A data frame containing Gazepoint Biometrics samples or
#'   summaries.
#' @param gp3tools_master A gp3tools-style master eye-tracking data frame.
#' @param ... Additional arguments passed to
#'   [join_gazepoint_biometrics_to_master()], including the required `by`
#'   argument when the underlying join helper requires explicit join columns.
#'
#' @return The output of [join_gazepoint_biometrics_to_master()].
#'
#' @examples
#' biometrics <- data.frame(USER = rep("P1", 3), CNT = 1:3, HR = c(70, 71, 72))
#' master <- data.frame(USER = rep("P1", 3), CNT = 1:3, AOI = c("A", "B", "A"))
#' join_gazepoint_biometrics_to_gp3tools(
#'   biometrics,
#'   master,
#'   by = c("USER", "CNT")
#' )
#'
#' @export
join_gazepoint_biometrics_to_gp3tools <- function(biometrics,
                                                  gp3tools_master,
                                                  ...) {
  if (!is.data.frame(biometrics)) {
    stop("`biometrics` must be a data frame.", call. = FALSE)
  }

  if (!is.data.frame(gp3tools_master)) {
    stop("`gp3tools_master` must be a data frame.", call. = FALSE)
  }

  args <- list(...)

  .gpbiom_call_with_two_data_args(
    target_function = join_gazepoint_biometrics_to_master,
    first_data = biometrics,
    second_data = gp3tools_master,
    args = args
  )
}


.gpbiom_call_with_data_first <- function(target_function, data, args) {
  formal_names <- names(formals(target_function))

  if (length(formal_names) == 0L) {
    stop("The target function does not expose formal arguments.", call. = FALSE)
  }

  data_arg <- formal_names[1L]

  do.call(
    target_function,
    c(stats::setNames(list(data), data_arg), args)
  )
}


.gpbiom_call_with_two_data_args <- function(target_function,
                                            first_data,
                                            second_data,
                                            args) {
  formal_names <- names(formals(target_function))

  if (length(formal_names) < 2L) {
    stop("The target function must expose at least two formal arguments.",
         call. = FALSE)
  }

  data_args <- stats::setNames(
    list(first_data, second_data),
    formal_names[1:2]
  )

  do.call(target_function, c(data_args, args))
}


.gpbiom_add_alias_argument <- function(args,
                                       target_function,
                                       aliases,
                                       value) {
  formal_names <- names(formals(target_function))

  existing_alias <- intersect(aliases, names(args))

  if (length(existing_alias) > 0L) {
    return(args)
  }

  supported_alias <- intersect(aliases, formal_names)

  if (length(supported_alias) > 0L) {
    args[[supported_alias[1L]]] <- value
  } else if ("..." %in% formal_names) {
    args[[aliases[1L]]] <- value
  }

  args
}
