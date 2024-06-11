from threading import Lock

import itables.options as opt
from itables import init_notebook_mode, show
from pandas import DataFrame


def display_df(
        df: DataFrame,
        layout: dict = None,
        buttons: list = None,
        length_menu: list = None
) -> None:
    """
    Display a pandas DataFrame using itables.
    iTables project page: https://github.com/mwouts/itables

    :param df: a pandas DataFrame # TODO add spark DataFrame support
    :param layout: layout options, refer to https://datatables.net/reference/option/layout
    :param buttons: buttons options, options refer to https://datatables.net/reference/button/
    :param length_menu: length menu options, refer to https://datatables.net/reference/option/lengthMenu
    :return:
    """
    # initialize itables for the notebook
    init_notebook_mode(all_interactive=False)

    # set default values if options are not provided
    default_layout = {
        "topStart": "search",
        "topEnd": "buttons",
        "bottomStart": "pageLength",
        "bottomEnd": "paging",
        "bottom2Start": "info"
    }
    default_buttons = ["csvHtml5", "excelHtml5", "print"]
    default_length_menu = [5, 10, 20]

    layout = layout or default_layout
    buttons = buttons or default_buttons
    length_menu = length_menu or default_length_menu

    lock = Lock()
    with lock:
        opt.layout = layout
        show(df, buttons=buttons, lengthMenu=length_menu)
