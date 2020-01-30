import pymanopt


# Package information
project = "Pymanopt"
author = "Jamie Townsend, Niklas Koep, Sebastian Weichwald"
copyright = "2016-2020, {:s}".format(author)
release = version = pymanopt.__version__

# Build settings
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.coverage",
    "sphinx.ext.mathjax",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode"
]
source_suffix = ".rst"
master_doc = "index"
language = None
exclude_patterns = ["build", "*.egg*"]

# Output options
html_theme = "sphinx_rtd_theme"
html_show_sphinx = False
html_baseurl = "www.pymanopt.org"
htmlhelp_basename = "pymanoptdoc"
html_last_updated_fmt = ""

# autodoc
autodoc_default_options = {
    "member-order": "bysource",
    "members": True,
    "undoc-members": True,
    "show-inheritance": True
}

# Napoleon settings
napoleon_google_docstring = False
napoleon_numpy_docstring = True
napoleon_include_special_with_doc = False
napoleon_include_private_with_doc = True
