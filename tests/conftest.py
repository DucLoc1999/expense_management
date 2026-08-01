from bot.i18n import load_locales


def pytest_configure(config):
    load_locales()
