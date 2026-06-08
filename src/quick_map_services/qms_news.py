import datetime
import os
from enum import Enum
from pathlib import Path
from typing import Optional

from quick_map_services.core import utils

plugin_dir = os.path.dirname(__file__)


class NewsLayout(str, Enum):
    """Available HTML layouts for QMS news."""

    DEFAULT = "default"
    ANNIVERSARY = "anniversary"


class News:
    """Represent localized news shown in the QMS search panel."""

    def __init__(
        self,
        qms_news,
        date_start: Optional[datetime.datetime] = None,
        date_finish: Optional[datetime.datetime] = None,
        icon: str = "news.png",
        layout: NewsLayout = NewsLayout.DEFAULT,
    ) -> None:
        """
        Initialize localized news.

        :param qms_news: Localized news text provider.
        :param date_start: Date and time to start showing the news.
        :param date_finish: Date and time to stop showing the news.
        :param icon: Icon filename from the plugin icons directory.
        :param layout: HTML layout identifier.
        """
        super(News, self).__init__()

        html = qms_news.get_text(utils.qgis_locale()) or ""
        icon_path = Path(plugin_dir) / "icons" / icon

        if layout == NewsLayout.ANNIVERSARY:
            self.html = self._anniversary_html(icon_path, html)
        else:
            self.html = self._default_html(icon_path, html)

        self.date_start = date_start
        if self.date_start is None:
            self.date_start = datetime.datetime.now()
        self.date_finish = date_finish

    @staticmethod
    def _default_html(icon_path: Path, html: str) -> str:
        return """
            <html>
            <head></head>
            <body>
                <center>
                    <table>
                        <tr>
                            <td><img src="{}"></td>
                            <td>&nbsp;{}</td>
                        </tr>
                    </table>
                </center>
            </body>
            </html>
        """.format(icon_path, html)

    @staticmethod
    def _anniversary_html(icon_path: Path, html: str) -> str:
        parts = html.split("<br>", 1)
        title = parts[0]
        subtitle = parts[1] if len(parts) > 1 else ""

        subtitle_row = ""
        if subtitle:
            subtitle_row = """
                        <tr>
                            <td style="padding-top: 2px; text-align: center;">
                                {}
                            </td>
                        </tr>
            """.format(subtitle)

        return """
            <html>
            <head></head>
            <body>
                <center>
                    <table cellspacing="0" cellpadding="0">
                        <tr>
                            <td rowspan="2"
                                style="vertical-align: middle;
                                       padding-right: 5px;">
                                <img src="{}">
                            </td>
                            <td style="font-weight: bold; text-align: center;">
                                {}
                            </td>
                            <td rowspan="2"
                                style="vertical-align: middle;
                                       padding-left: 5px;">
                                <img src="{}">
                            </td>
                        </tr>
                        {}
                    </table>
                </center>
            </body>
            </html>
        """.format(icon_path, title, icon_path, subtitle_row)

    def is_time_to_show(self) -> bool:
        """
        Check whether the news should be shown now.

        :return: True if current time is inside the news period.
        """
        current_timestamp = datetime.datetime.now().timestamp()
        if self.date_start.timestamp() > current_timestamp:
            return False

        if self.date_finish is None:
            return True

        return self.date_finish.timestamp() > current_timestamp
