import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import gspread

from services.sheets import _get_worksheet, HEADERS


@pytest.fixture
def mock_gspread():
    mock_client = MagicMock()
    mock_spreadsheet = MagicMock()

    mock_ws = MagicMock()
    mock_ws.id = 98765

    with (
        patch("services.sheets._get_client", return_value=mock_client),
        patch.object(mock_client, "open_by_key", return_value=mock_spreadsheet),
    ):
        yield {
            "client": mock_client,
            "spreadsheet": mock_spreadsheet,
            "ws": mock_ws,
        }


@pytest.fixture
def mock_db():
    with (
        patch("services.sheets.get_sheet_id", new_callable=AsyncMock) as get_sid,
        patch("services.sheets.set_sheet_id", new_callable=AsyncMock) as set_sid,
    ):
        yield {"get_sheet_id": get_sid, "set_sheet_id": set_sid}


@pytest.mark.asyncio
class TestGetWorksheet:
    async def test_id_based_lookup(self, mock_gspread, mock_db):
        mock_gspread["spreadsheet"].get_worksheet_by_id.return_value = mock_gspread["ws"]
        mock_db["get_sheet_id"].return_value = 98765

        ws = await _get_worksheet(tele_user_id=111)

        assert ws is mock_gspread["ws"]
        mock_gspread["spreadsheet"].get_worksheet_by_id.assert_called_once_with(98765)
        mock_gspread["spreadsheet"].worksheet.assert_not_called()
        mock_db["set_sheet_id"].assert_not_called()

    async def test_rename_scenario(self, mock_gspread, mock_db):
        mock_gspread["spreadsheet"].get_worksheet_by_id.return_value = mock_gspread["ws"]
        mock_db["get_sheet_id"].return_value = 98765

        ws = await _get_worksheet(tele_user_id=111)

        assert ws is mock_gspread["ws"]
        mock_gspread["spreadsheet"].get_worksheet_by_id.assert_called_once_with(98765)

    async def test_delete_scenario(self, mock_gspread, mock_db):
        mock_gspread["spreadsheet"].get_worksheet_by_id.side_effect = gspread.WorksheetNotFound("deleted")
        mock_gspread["spreadsheet"].worksheet.side_effect = gspread.WorksheetNotFound("not found")
        mock_gspread["spreadsheet"].add_worksheet.return_value = mock_gspread["ws"]
        mock_db["get_sheet_id"].return_value = 98765

        ws = await _get_worksheet(tele_user_id=111)

        assert ws is mock_gspread["ws"]
        mock_gspread["spreadsheet"].get_worksheet_by_id.assert_called_once_with(98765)
        mock_gspread["spreadsheet"].worksheet.assert_called_once_with("111")
        mock_gspread["spreadsheet"].add_worksheet.assert_called_once_with(title="111", rows=1000, cols=len(HEADERS))
        mock_db["set_sheet_id"].assert_awaited_once_with(111, 98765)

    async def test_null_sheet_id_title_fallback(self, mock_gspread, mock_db):
        mock_gspread["spreadsheet"].worksheet.return_value = mock_gspread["ws"]
        mock_db["get_sheet_id"].return_value = None

        ws = await _get_worksheet(tele_user_id=111)

        assert ws is mock_gspread["ws"]
        mock_gspread["spreadsheet"].get_worksheet_by_id.assert_not_called()
        mock_gspread["spreadsheet"].worksheet.assert_called_once_with("111")
        mock_db["set_sheet_id"].assert_awaited_once_with(111, 98765)

    async def test_first_time_no_tab_no_sheet_id(self, mock_gspread, mock_db):
        mock_gspread["spreadsheet"].worksheet.side_effect = gspread.WorksheetNotFound("not found")
        mock_gspread["spreadsheet"].add_worksheet.return_value = mock_gspread["ws"]
        mock_db["get_sheet_id"].return_value = None

        ws = await _get_worksheet(tele_user_id=111)

        assert ws is mock_gspread["ws"]
        mock_gspread["spreadsheet"].add_worksheet.assert_called_once_with(title="111", rows=1000, cols=len(HEADERS))
        mock_db["set_sheet_id"].assert_awaited_once_with(111, 98765)

    async def test_delete_then_recreate_persists_new_id(self, mock_gspread, mock_db):
        old_ws = MagicMock()
        old_ws.id = 11111
        new_ws = MagicMock()
        new_ws.id = 22222

        mock_gspread["spreadsheet"].get_worksheet_by_id.side_effect = gspread.WorksheetNotFound("deleted")
        mock_gspread["spreadsheet"].worksheet.side_effect = gspread.WorksheetNotFound("not found")
        mock_gspread["spreadsheet"].add_worksheet.return_value = new_ws
        mock_db["get_sheet_id"].return_value = 11111

        ws = await _get_worksheet(tele_user_id=111)

        assert ws is new_ws
        assert ws.id == 22222
        mock_db["set_sheet_id"].assert_awaited_once_with(111, 22222)
