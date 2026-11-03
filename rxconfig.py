import reflex as rx

config = rx.Config(
    app_name="prismal_webchat",
    # ARCHITECTURE §3: the app is assembled in prismal_webchat/webchat.py.
    app_module_import="prismal_webchat.webchat",
    # prismal-server's local default is :8000 (SPEC-WCB-APP-004); keep the
    # webchat's own Reflex backend off that port.
    frontend_port=3000,
    backend_port=8001,
    plugins=[rx.plugins.RadixThemesPlugin()],
    # The prod badge would cover the embedded widget's Send button.
    show_built_with_reflex=False,
    # An embedded widget has nothing to index.
    disable_plugins=[rx.plugins.SitemapPlugin],
)
