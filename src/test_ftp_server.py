"""Functional tests for the ftplink FTP-to-Telegram bridge.

Network access (the object-detection endpoint and Telegram) is fully mocked so
the suite runs offline in CI. These tests are the gate that decides whether a
Renovate dependency update may be auto-merged: if a bump breaks the detection
filtering or the file routing, the tests fail and the pull request stays open
for a human to inspect instead of being merged.
"""
import os
import sys
from unittest import mock

import pytest

sys.path.insert(0, os.path.dirname(__file__))

import ftp_server  # noqa: E402


def _detection_response(status=200, payload=None):
    resp = mock.Mock()
    resp.status_code = status
    resp.text = 'error'
    resp.json.return_value = payload if payload is not None else []
    return resp


def test_allowed_objects_default_contains_person():
    assert 'person' in ftp_server.allowed_objects


def test_is_allowed_by_detection_true_for_matching_object(monkeypatch):
    monkeypatch.setattr(ftp_server, 'detection_endpoint', 'http://detect')
    monkeypatch.setattr(ftp_server, 'allowed_objects', {'person'})
    resp = _detection_response(payload=[{'objects': [{'name': 'Person'}]}])
    with mock.patch('builtins.open', mock.mock_open(read_data=b'img')):
        with mock.patch.object(ftp_server.requests, 'post', return_value=resp):
            assert ftp_server.is_allowed_by_detection('/tmp/x.jpg') is True


def test_is_allowed_by_detection_false_for_non_matching_object(monkeypatch):
    monkeypatch.setattr(ftp_server, 'detection_endpoint', 'http://detect')
    monkeypatch.setattr(ftp_server, 'allowed_objects', {'person'})
    resp = _detection_response(payload=[{'objects': [{'name': 'cat'}]}])
    with mock.patch('builtins.open', mock.mock_open(read_data=b'img')):
        with mock.patch.object(ftp_server.requests, 'post', return_value=resp):
            assert ftp_server.is_allowed_by_detection('/tmp/x.jpg') is False


def test_detection_error_falls_back_to_sending(monkeypatch):
    """On a detection failure the file must still be delivered (fail-open)."""
    monkeypatch.setattr(ftp_server, 'detection_endpoint', 'http://detect')
    sent = []
    monkeypatch.setattr(ftp_server, 'send_to_telegram', lambda p: sent.append(p))
    monkeypatch.setattr(ftp_server, 'notify_telegram_error', lambda m: None)
    with mock.patch('builtins.open', mock.mock_open(read_data=b'img')):
        with mock.patch.object(ftp_server.requests, 'post',
                               return_value=_detection_response(status=500)):
            assert ftp_server.is_allowed_by_detection('/tmp/x.jpg') is False
    assert sent == ['/tmp/x.jpg']


def test_on_file_received_deletes_filtered_file(monkeypatch, tmp_path):
    monkeypatch.setattr(ftp_server, 'detection_endpoint', 'http://detect')
    monkeypatch.setattr(ftp_server, 'is_allowed_by_detection', lambda p: False)
    sent = []
    monkeypatch.setattr(ftp_server, 'send_to_telegram', lambda p: sent.append(p))
    f = tmp_path / 'blocked.jpg'
    f.write_bytes(b'data')

    handler = ftp_server.Telegram.__new__(ftp_server.Telegram)
    handler.on_file_received(str(f))

    assert not f.exists()
    assert sent == []


def test_on_file_received_sends_allowed_file(monkeypatch, tmp_path):
    monkeypatch.setattr(ftp_server, 'detection_endpoint', 'http://detect')
    monkeypatch.setattr(ftp_server, 'is_allowed_by_detection', lambda p: True)
    sent = []
    monkeypatch.setattr(ftp_server, 'send_to_telegram', lambda p: sent.append(p))

    handler = ftp_server.Telegram.__new__(ftp_server.Telegram)
    handler.on_file_received('/tmp/allowed.jpg')

    assert sent == ['/tmp/allowed.jpg']


def test_on_file_received_without_endpoint_always_sends(monkeypatch):
    monkeypatch.setattr(ftp_server, 'detection_endpoint', '')
    sent = []
    monkeypatch.setattr(ftp_server, 'send_to_telegram', lambda p: sent.append(p))

    handler = ftp_server.Telegram.__new__(ftp_server.Telegram)
    handler.on_file_received('/tmp/anything.mp4')

    assert sent == ['/tmp/anything.mp4']


def test_send_to_telegram_sends_photo_and_removes(monkeypatch):
    bot = mock.Mock()
    monkeypatch.setattr(ftp_server.telegram, 'Bot', lambda token: bot)
    removed = []
    monkeypatch.setattr(ftp_server.os, 'remove', lambda p: removed.append(p))
    monkeypatch.setattr(ftp_server.asyncio, 'run', lambda coro: coro)

    ftp_server.send_to_telegram('/tmp/pic.JPG')

    bot.sendPhoto.assert_called_once()
    assert removed == ['/tmp/pic.JPG']


def test_send_to_telegram_sends_video_for_mp4(monkeypatch):
    bot = mock.Mock()
    monkeypatch.setattr(ftp_server.telegram, 'Bot', lambda token: bot)
    monkeypatch.setattr(ftp_server.os, 'remove', lambda p: None)
    monkeypatch.setattr(ftp_server.asyncio, 'run', lambda coro: coro)

    ftp_server.send_to_telegram('/tmp/clip.mp4')

    bot.sendVideo.assert_called_once()


def test_send_to_telegram_ignores_unknown_extension(monkeypatch):
    bot = mock.Mock()
    monkeypatch.setattr(ftp_server.telegram, 'Bot', lambda token: bot)
    monkeypatch.setattr(ftp_server.asyncio, 'run', lambda coro: coro)

    ftp_server.send_to_telegram('/tmp/notes.txt')

    bot.sendPhoto.assert_not_called()
    bot.sendVideo.assert_not_called()


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-v']))
