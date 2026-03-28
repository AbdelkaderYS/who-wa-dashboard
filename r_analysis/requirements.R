# r_analysis/requirements.R
# Install required R packages
# Run once: Rscript r_analysis/requirements.R

packages <- c("readr", "dplyr", "tidyr", "ggplot2", "forecast", "broom", "knitr", "rmarkdown")

for (pkg in packages) {
  if (!require(pkg, character.only = TRUE, quietly = TRUE)) {
    install.packages(pkg, repos = "https://cran.rstudio.com/")
  }
}

cat("All R packages installed.\n")
