import os

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QMessageBox, QWidget

from .line_edit_color_validator import LineEditColorValidator

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "editor_widget_mvt.ui")
)


class EditorWidgetMvt(QWidget, FORM_CLASS):
    def __init__(self, parent=None):
        super(EditorWidgetMvt, self).__init__(parent)
        self.setupUi(self)
        self.mvt_url_validator = LineEditColorValidator(
            self.txtUrl,
            "http[s]?://.+",
            error_tooltip="http{s}://any_text/{z}/{x}/{y}.mvt",
        )
        self.style_url_validator = LineEditColorValidator(
            self.txtStyleUrl,
            "http[s]?://.+",
            error_tooltip="http{s}://any_text/style.json",
        )

    def fill_form(self, ds_info):
        self.txtUrl.setText(ds_info.mvt_url)
        self.txtStyleUrl.setText(ds_info.mvt_style_url)
        self.spbZMin.setValue(
            int(ds_info.mvt_zmin) if ds_info.mvt_zmin is not None else 0
        )
        self.spbZMax.setValue(
            int(ds_info.mvt_zmax) if ds_info.mvt_zmax is not None else 14
        )

    def fill_ds_info(self, ds_info):
        ds_info.mvt_url = self.txtUrl.text()
        ds_info.mvt_style_url = self.txtStyleUrl.text()
        ds_info.mvt_zmin = self.spbZMin.value()
        ds_info.mvt_zmax = self.spbZMax.value()

    def validate(self, ds_info):
        if not ds_info.mvt_url:
            QMessageBox.critical(
                self,
                self.tr("Error on save data source"),
                self.tr("Please, enter MVT url"),
            )
            return False

        if not self.mvt_url_validator.is_valid():
            QMessageBox.critical(
                self,
                self.tr("Error on save data source"),
                self.tr("Please, enter correct value for MVT url"),
            )
            return False

        if not ds_info.mvt_style_url:
            QMessageBox.critical(
                self,
                self.tr("Error on save data source"),
                self.tr("Please, enter MVT style url"),
            )
            return False

        if not self.style_url_validator.is_valid():
            QMessageBox.critical(
                self,
                self.tr("Error on save data source"),
                self.tr("Please, enter correct value for MVT style url"),
            )
            return False

        if ds_info.mvt_zmin > ds_info.mvt_zmax:
            QMessageBox.critical(
                self,
                self.tr("Error on save data source"),
                self.tr("MVT z min should be less than or equal to z max"),
            )
            return False

        return True
