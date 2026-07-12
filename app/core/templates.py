"""Mako 模板引擎設定。"""

from mako.lookup import TemplateLookup

templates = TemplateLookup(
    directories=["templates"], default_filters=["h"],
)
