#' Run automated exploratory statistics for Gazepoint feature tables
#'
#' Runs simple exploratory group comparisons for numeric feature columns.
#' The function selects one-way ANOVA when all groups pass Shapiro-Wilk checks
#' and Kruskal-Wallis otherwise. It also performs pairwise post-hoc tests with
#' multiplicity correction.
#'
#' This is an exploratory reporting helper. It is not a substitute for a
#' preregistered statistical model or expert review of study design.
#'
#' @param dat A data frame.
#' @param outcome_cols Numeric outcome columns.
#' @param group_col Grouping/condition column.
#' @param alpha Significance level.
#' @param p_adjust_method P-value adjustment method.
#' @param normality_alpha Alpha used for Shapiro-Wilk normality screening.
#' @param min_group_n Minimum observations per group.
#'
#' @return A list with `overview`, `test_table`, `posthoc_table`,
#'   `normality_table`, and `settings`.
#' @export
run_gazepoint_automated_statistics <- function(dat,
                                               outcome_cols,
                                               group_col,
                                               alpha = 0.05,
                                               p_adjust_method = "holm",
                                               normality_alpha = 0.05,
                                               min_group_n = 3) {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  required <- c(outcome_cols, group_col)
  missing_required <- setdiff(required, names(dat))

  if (length(missing_required) > 0) {
    stop("Missing required columns: ", paste(missing_required, collapse = ", "), call. = FALSE)
  }

  non_numeric <- outcome_cols[!vapply(dat[outcome_cols], is.numeric, logical(1))]
  if (length(non_numeric) > 0) {
    stop("These `outcome_cols` are not numeric: ", paste(non_numeric, collapse = ", "), call. = FALSE)
  }

  test_rows <- list()
  normality_rows <- list()
  posthoc_rows <- list()
  test_id <- 1L
  norm_id <- 1L
  posthoc_id <- 1L

  for (outcome in outcome_cols) {
    d <- dat[, c(outcome, group_col), drop = FALSE]
    names(d) <- c("outcome", "group")
    d <- d[is.finite(d$outcome) & !is.na(d$group), , drop = FALSE]
    d$group <- as.factor(d$group)

    group_counts <- table(d$group)

    if (nrow(d) < min_group_n * 2 || length(group_counts) < 2 || any(group_counts < min_group_n)) {
      test_rows[[test_id]] <- data.frame(
        outcome = outcome,
        test = NA_character_,
        statistic = NA_real_,
        df1 = NA_real_,
        df2 = NA_real_,
        p_value = NA_real_,
        p_adjusted = NA_real_,
        normality_screen_passed = NA,
        status = "insufficient_group_data",
        stringsAsFactors = FALSE
      )
      test_id <- test_id + 1L
      next
    }

    group_levels <- levels(d$group)
    normality_p <- numeric(length(group_levels))

    for (i in seq_along(group_levels)) {
      x <- d$outcome[d$group == group_levels[i]]
      normality_p[i] <- gpbiometrics_auto_stats_shapiro(x)

      normality_rows[[norm_id]] <- data.frame(
        outcome = outcome,
        group = group_levels[i],
        n = length(x),
        shapiro_p = normality_p[i],
        normality_passed = is.finite(normality_p[i]) && normality_p[i] >= normality_alpha,
        stringsAsFactors = FALSE
      )
      norm_id <- norm_id + 1L
    }

    normality_passed <- all(is.finite(normality_p) & normality_p >= normality_alpha)

    if (normality_passed) {
      fit <- stats::aov(outcome ~ group, data = d)
      tab <- summary(fit)[[1]]
      statistic <- unname(tab$`F value`[1])
      p_value <- unname(tab$`Pr(>F)`[1])
      df1 <- unname(tab$Df[1])
      df2 <- unname(tab$Df[2])
      test_name <- "one_way_anova"

      pairwise <- stats::pairwise.t.test(
        x = d$outcome,
        g = d$group,
        p.adjust.method = p_adjust_method,
        pool.sd = FALSE
      )
    } else {
      kt <- stats::kruskal.test(outcome ~ group, data = d)
      statistic <- unname(kt$statistic)
      p_value <- kt$p.value
      df1 <- unname(kt$parameter)
      df2 <- NA_real_
      test_name <- "kruskal_wallis"

      pairwise <- stats::pairwise.wilcox.test(
        x = d$outcome,
        g = d$group,
        p.adjust.method = p_adjust_method,
        exact = FALSE
      )
    }

    test_rows[[test_id]] <- data.frame(
      outcome = outcome,
      test = test_name,
      statistic = statistic,
      df1 = df1,
      df2 = df2,
      p_value = p_value,
      p_adjusted = NA_real_,
      normality_screen_passed = normality_passed,
      status = "test_completed",
      stringsAsFactors = FALSE
    )
    test_id <- test_id + 1L

    posthoc_dat <- gpbiometrics_auto_stats_pairwise_table(pairwise$p.value, outcome)

    if (nrow(posthoc_dat) > 0) {
      for (i in seq_len(nrow(posthoc_dat))) {
        posthoc_rows[[posthoc_id]] <- posthoc_dat[i, , drop = FALSE]
        posthoc_id <- posthoc_id + 1L
      }
    }
  }

  test_table <- do.call(rbind, test_rows)
  rownames(test_table) <- NULL

  if (any(is.finite(test_table$p_value))) {
    ok <- is.finite(test_table$p_value)
    test_table$p_adjusted[ok] <- stats::p.adjust(test_table$p_value[ok], method = p_adjust_method)
  }

  normality_table <- if (length(normality_rows) > 0) {
    do.call(rbind, normality_rows)
  } else {
    data.frame()
  }

  posthoc_table <- if (length(posthoc_rows) > 0) {
    do.call(rbind, posthoc_rows)
  } else {
    data.frame()
  }

  if (nrow(posthoc_table) > 0 && "p_adjusted" %in% names(posthoc_table)) {
    posthoc_table$significant <- is.finite(posthoc_table$p_adjusted) &
      posthoc_table$p_adjusted < alpha
  }

  overview <- data.frame(
    outcome_count = length(outcome_cols),
    completed_tests = sum(test_table$status == "test_completed"),
    insufficient_tests = sum(test_table$status != "test_completed"),
    significant_tests = sum(is.finite(test_table$p_adjusted) & test_table$p_adjusted < alpha),
    posthoc_rows = nrow(posthoc_table),
    status = if (all(test_table$status == "test_completed")) {
      "automated_statistics_complete"
    } else if (any(test_table$status == "test_completed")) {
      "automated_statistics_partial"
    } else {
      "automated_statistics_failed"
    },
    interpretation = paste(
      "Automated statistics are exploratory convenience summaries.",
      "They should be reviewed against the study design and are not a substitute for preregistered modelling."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      test_table = test_table,
      posthoc_table = posthoc_table,
      normality_table = normality_table,
      settings = list(
        outcome_cols = outcome_cols,
        group_col = group_col,
        alpha = alpha,
        p_adjust_method = p_adjust_method,
        normality_alpha = normality_alpha,
        min_group_n = min_group_n
      )
    ),
    class = c("gazepoint_automated_statistics", "list")
  )
}

gpbiometrics_auto_stats_shapiro <- function(x) {
  x <- x[is.finite(x)]

  if (length(x) < 3 || length(x) > 5000 || stats::sd(x) == 0) {
    return(NA_real_)
  }

  stats::shapiro.test(x)$p.value
}

gpbiometrics_auto_stats_pairwise_table <- function(p_matrix, outcome) {
  if (is.null(p_matrix) || length(p_matrix) == 0) {
    return(data.frame())
  }

  rows <- list()
  row_id <- 1L

  for (i in seq_len(nrow(p_matrix))) {
    for (j in seq_len(ncol(p_matrix))) {
      p <- p_matrix[i, j]

      if (is.finite(p)) {
        rows[[row_id]] <- data.frame(
          outcome = outcome,
          group_1 = rownames(p_matrix)[i],
          group_2 = colnames(p_matrix)[j],
          p_adjusted = p,
          stringsAsFactors = FALSE
        )
        row_id <- row_id + 1L
      }
    }
  }

  if (length(rows) == 0) {
    return(data.frame())
  }

  do.call(rbind, rows)
}
