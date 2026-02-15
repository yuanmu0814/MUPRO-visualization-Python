from PyQt5 import QtCore


def domain_processing(view, filedir: str) -> int:
    column_number = view.loadData(filedir)
    view.outputDomain(filedir, view.xmax, view.ymax, view.zmax)

    for i in range(5):
        item = view.domain_TW.item(i, 0)
        if item is not None:
            item.setCheckState(QtCore.Qt.Checked)

    for i in range(27):
        item = view.domain_TW.item(i + 4, 0)
        if item is None:
            continue
        if view.existDomain[i]:
            item.setCheckState(QtCore.Qt.Checked)
        else:
            item.setCheckState(QtCore.Qt.Unchecked)

    return column_number
