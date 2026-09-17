"""
Crinômetro - Folhas de Estilo Globais (QSS) e Temas (Dark / Light).
"""

DARK_STYLESHEET = r"""            QMainWindow, QWidget {
                background: #0D0F11;
                color: #E8EAED;
                font-family: 'Segoe UI', 'Arial';
            }
            QLabel {
                background: transparent;
                border: 0;
            }
            QLabel#eyebrow, QLabel#summaryFile, QLabel#summaryMeta,
            QLabel#metricTitle, QLabel#metricValue, QLabel#metricSub,
            QLabel#brand, QLabel#version, QLabel#plotTitle {
                background: transparent;
                border: 0;
            }
            QSplitter::handle {
                background: #181B1F;
            }
            QSplitter#dashboardSplitter::handle:horizontal {
                background: #15181C;
                width: 6px;
                margin: 0px 1px;
                border-radius: 3px;
            }
            QSplitter#dashboardSplitter::handle:horizontal:hover {
                background: #2563EB;
            }
            QSplitter#stackSplitter::handle:vertical {
                background: #15181C;
                height: 6px;
                margin: 1px 0px;
                border-radius: 3px;
            }
            QSplitter#stackSplitter::handle:vertical:hover {
                background: #2563EB;
            }
            QFrame#topNav {
                background: transparent;
                border-bottom: 1px solid #292D32;
            }
            QLabel#brand {
                color: #F3F4F6;
                font-size: 18px;
                font-weight: 600;
            }
            QLabel#version {
                color: #7E848D;
                font-size: 12px;
            }
            QLabel#themeLabel { color: #8B939C; font-size: 11px; font-weight: 600; background: transparent; }
            QPushButton#menuButton, QPushButton#navIcon, QPushButton#playButton {
                background: transparent;
                border: 0;
                color: #AEB3BB;
                border-radius: 6px;
                font-size: 18px;
                padding: 0;
                outline: none;
            }
            QPushButton#menuButton:hover, QPushButton#navIcon:hover {
                background: #23272C;
                color: #FFFFFF;
            }
            QLabel#profileAvatar {
                background: #26313B;
                color: #E8F1F8;
                border: 1px solid #42515D;
                border-radius: 18px;
                font-size: 12px;
                font-weight: 700;
                qproperty-alignment: AlignCenter;
            }
            QPushButton#btn_sync {
                background: #1E293B;
                color: #CBD5E1;
                border: 1px solid #334155;
                border-radius: 5px;
                min-width: 26px;
                max-width: 26px;
                min-height: 26px;
                max-height: 26px;
                padding: 0px;
            }
            QPushButton#btn_sync:hover {
                background: #334155;
                color: #FFFFFF;
                border-color: #60A5FA;
            }
            QPushButton#btn_sync:checked {
                background: #2563EB;
                color: #FFFFFF;
                border-color: #3B82F6;
            }
            QFrame#sidebar {
                background: #111316;
                border-right: 1px solid #272A2F;
            }
            QLabel#sidebarTitle {
                background: transparent;
                color: #BFC3CA;
                font-size: 12px;
                font-weight: 600;
            }
            QListWidget {
                background: transparent;
                border: 0;
                outline: 0;
                padding: 2px 4px 4px 4px;
                color: #BFC3CA;
                font-size: 12px;
            }
            QListWidget::item {
                background: transparent;
                border: none;
                padding: 0;
                margin: 2px 0;
            }
            QListWidget::item:selected {
                background: transparent;
                border: none;
            }
            QListWidget::item:hover {
                background: transparent;
                border: none;
            }
            QFrame#audioFileCard {
                background: #171A1E;
                border: 1px solid #282C32;
                border-radius: 6px;
            }
            QFrame#audioFileCard:hover {
                background: #23282F;
                border: 1px solid #3A424D;
            }
            QFrame#audioFileCard[active="true"] {
                background: #193A58;
                border: 1px solid #2D8CD8;
            }
            QLabel#audioFileName {
                color: #D1D5DB;
                font-size: 12px;
                font-weight: 500;
            }
            QFrame#audioFileCard[active="true"] QLabel#audioFileName {
                color: #FFFFFF;
                font-weight: 600;
            }
            QScrollBar:horizontal {
                height: 0px;
                width: 0px;
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #2D333B;
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: #47505D;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
                border: none;
                height: 0px;
            }
            QFrame#summaryCard, QFrame#transportTimelineCard, QFrame#timelineCard {
                background: #17191C;
                border: 1px solid #292D32;
                border-radius: 10px;
            }
            QFrame#plotCard, QWidget#plotCard {
                background: #14171A;
                border: 1px solid #2B3037;
                border-radius: 14px;
            }
            QFrame#plotCard:hover, QWidget#plotCard:hover {
                border-color: #383F4A;
            }
            QFrame#plotCard[mainPlot="true"], QWidget#plotCard[mainPlot="true"] {
                border: 1.5px solid #2563EB;
                border-radius: 14px;
            }
            QWidget#plotTitleBar {
                background: #191D22;
                border-top-left-radius: 13px;
                border-top-right-radius: 13px;
                border-bottom: 1px solid #23272D;
            }
            QLabel#eyebrow {
                color: #9CA2AA;
                font-size: 12px;
                font-weight: 500;
            }
            QLabel#summaryFile {
                color: #F0F2F4;
                font-size: 26px;
                font-weight: 600;
            }
            QLabel#summaryMeta {
                color: #8E949C;
                font-size: 10px;
            }
            QLabel#metricTitle { color: #9EA4AC; font-size: 12px; }
            QLabel#metricValue { color: #F5F6F7; font-size: 27px; font-weight: 600; }
            QLabel#metricSub { color: #A5AAB2; font-size: 11px; }
            QLabel#volumeLabel { background: transparent; color: #7F8790; font-size: 10px; font-weight: 600; }
            QWidget#volumeCluster { background: transparent; border: 0; }
            QLabel#metricDivider { color: #363A40; }
            /* Ação Primária do Cabeçalho (Reanalisar) */
            QPushButton#summaryPrimaryAction {
                background-color: #2563EB;
                color: #FFFFFF;
                border: 1px solid #3B82F6;
                border-radius: 5px;
                min-height: 18px;
                max-height: 18px;
                padding: 4px 12px;
                font-size: 12px;
                font-weight: 600;
                outline: none;
            }
            QPushButton#summaryPrimaryAction:hover {
                background-color: #1D4ED8;
                border-color: #60A5FA;
            }
            QPushButton#summaryPrimaryAction:pressed {
                background-color: #1E40AF;
                border-color: #1D4ED8;
            }

            /* Alternância de Inteligência Artificial (Pill Toggle) */
            QPushButton#summaryToggleMl {
                min-height: 18px;
                max-height: 18px;
                border-radius: 14px;
                padding: 4px 12px;
                font-size: 11.5px;
                font-weight: 600;
                outline: none;
            }
            QPushButton#summaryToggleMl[active="true"] {
                background-color: #064E3B;
                border: 1px solid #059669;
                color: #34D399;
            }
            QPushButton#summaryToggleMl[active="true"]:hover {
                background-color: #065F46;
                border-color: #10B981;
                color: #6EE7B7;
            }
            QPushButton#summaryToggleMl[active="false"] {
                background-color: #1E2530;
                border: 1px solid #2D3748;
                color: #94A3B8;
            }
            QPushButton#summaryToggleMl[active="false"]:hover {
                background-color: #283344;
                border-color: #4A5568;
                color: #CBD5E1;
            }

            /* Ações Secundárias do Cabeçalho */
            QPushButton#summaryAction, QPushButton.summarySecondaryAction {
                background-color: #1E2530;
                color: #E2E8F0;
                border: 1px solid #2D3748;
                border-radius: 5px;
                min-height: 18px;
                max-height: 18px;
                padding: 4px 10px;
                font-size: 12px;
                font-weight: 500;
                outline: none;
            }
            QPushButton#summaryAction:hover, QPushButton.summarySecondaryAction:hover {
                background-color: #283344;
                border-color: #4A5568;
                color: #FFFFFF;
            }
            QPushButton#summaryAction:pressed, QPushButton.summarySecondaryAction:pressed {
                background-color: #171D26;
                border-color: #1F2937;
            }
            QPushButton#summaryAction:disabled, QPushButton.summarySecondaryAction:disabled {
                background-color: #181B1F;
                color: #4B5563;
                border-color: #23272D;
            }

            /* Slider Vertical do Eixo Y do Espectrograma */
            QSlider#specYSlider {
                background: transparent;
                border: none;
                width: 16px;
                margin: 4px 0px;
            }
            QSlider#specYSlider::groove:vertical {
                width: 3px;
                background: rgba(255, 255, 255, 0.12);
                border: none;
                border-radius: 1.5px;
            }
            QSlider#specYSlider::sub-page:vertical {
                background: rgba(255, 255, 255, 0.12);
                border-radius: 1.5px;
            }
            QSlider#specYSlider::add-page:vertical {
                background: #2563EB;
                border-radius: 1.5px;
            }
            QSlider#specYSlider::handle:vertical {
                background: #38BDF8;
                border: 1px solid #0284C7;
                width: 10px;
                height: 10px;
                margin: 0 -3.5px;
                border-radius: 5px;
            }
            QSlider#specYSlider::handle:vertical:hover {
                background: #7DD3FC;
                border: 1px solid #38BDF8;
            }
            QWidget#plotTitleBar {
                background: #191C20;
                border: 0;
                border-bottom: 1px solid #262A30;
                border-top-left-radius: 11px;
                border-top-right-radius: 11px;
            }
            QLabel#plotTitle {
                background: transparent;
                padding: 0;
                color: #D8DBDF;
                font-size: 11.5px;
                font-weight: 600;
            }
            QPushButton#plotTool {
                background: transparent;
                border: 0;
                color: #AEB4BD;
                border-radius: 5px;
                font-size: 15px;
                padding: 3px;
                outline: none;
            }
            QPushButton#plotTool:hover { background: #2A3038; color: #60A5FA; }
            QPushButton#plotTool:pressed { background: #1D2024; }
            QPushButton#plotTool:disabled { color: #4B5563; background: transparent; }
            QPushButton#plotMaximize {
                color: #C7CCD2;
                font-size: 16px;
                border-radius: 5px;
                padding: 3px;
            }
            QPushButton#plotMaximize:hover { background: #2A3038; color: #60A5FA; }
            QPushButton#plotClose {
                background: transparent;
                border: 0;
                color: #AEB4BD;
                border-radius: 5px;
                font-size: 11px;
                font-weight: bold;
                padding: 3px;
                outline: none;
            }
            QPushButton#plotClose:hover {
                background: rgba(239, 68, 68, 0.25);
                color: #EF4444;
            }
            QPushButton#navIcon, QPushButton#menuButton {
                color: #AEB4BD; background: transparent; border: 0; border-radius: 6px;
            }
            QPushButton#navIcon:hover, QPushButton#menuButton:hover {
                background: #252A30; color: #60A5FA;
            }
            QSlider#volumeSlider { background: transparent; border: none; min-height: 16px; padding: 0; margin: 0; }
            QSlider#volumeSlider::add-page:horizontal { background: transparent; }
            QSlider#volumeSlider::groove:horizontal {
                height: 5px; background: #30343A; border-radius: 2px;
            }
            QSlider#volumeSlider::sub-page:horizontal {
                background: #3B93D8; border-radius: 2px;
            }
            QSlider#volumeSlider::handle:horizontal {
                width: 12px; height: 12px; margin: -4px 0;
                background: #DDE2E7; border: 0; border-radius: 6px;
            }
            QPushButton#transport, QPushButton#speedButton {
                background: transparent;
                color: #B8BDC5;
                border: 0;
                border-radius: 20px;
                padding: 0;
                outline: none;
            }
            QPushButton#transport:hover, QPushButton#speedButton:hover { background: #25292E; color: #F7F8FA; }
            QPushButton#playButton {
                background: #2E8DD9;
                outline: none;
                border: 0;
                color: white;
                border-radius: 22px;
            }
            QPushButton#playButton:hover { background: #3A9BE7; }
            QPushButton#playButton:focus { outline: none; border: 0; }
            QPushButton#playButton:pressed { background: #2579B9; outline: none; border: 0; }
            QPushButton#speedButton {
                font-size: 11px;
                font-weight: 600;
                color: #AEB4BD;
            }
            QMenu {
                background-color: #1E232A;
                color: #E2E8F0;
                border: 1px solid #384252;
                border-radius: 8px;
                padding: 6px;
            }
            QMenu::item {
                padding: 8px 26px 8px 12px;
                border-radius: 6px;
                margin: 2px 2px;
                background-color: transparent;
                color: #E2E8F0;
                font-size: 12px;
            }
            QMenu::item:selected {
                background-color: #2563EB;
                color: #FFFFFF;
                font-weight: 600;
            }
            QMenu::item:pressed {
                background-color: #1D4ED8;
                color: #FFFFFF;
            }
            QMenu::separator {
                height: 1px;
                background-color: #2E3846;
                margin: 5px 6px;
            }
            QMenu::right-arrow {
                margin-right: 8px;
            }
            QToolTip { background: #22262B; color: #F0F2F4; border: 1px solid #3B4047; }
            QLabel#elapsedLabel { color: #AEB4BD; background: transparent; border: 0; padding: 0; }
            QFrame#playbackCard { background: transparent; border: 0; }
            QWidget#playCenter { background: transparent; border: 0; }
            QCheckBox { spacing: 6px; color: #D1D5DB; background: transparent; }
            QCheckBox::indicator { width: 14px; height: 14px; border-radius: 3px; border: 1px solid #4B5563; background-color: #1F242C; }
            QCheckBox::indicator:hover { border-color: #3B82F6; }
            QCheckBox::indicator:checked { background-color: #2563EB; border-color: #2563EB; }
            QScrollBar:vertical {
                background: transparent;
                width: 10px;
                margin: 4px 2px 4px 2px;
                border-radius: 5px;
                border: none;
            }
            QScrollBar::track:vertical {
                background-color: #16191E;
                border-radius: 5px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background-color: #64748B;
                min-height: 28px;
                border-radius: 5px;
                border: none;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #94A3B8;
            }
            QScrollBar::handle:vertical:pressed {
                background-color: #475569;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px; width: 0px; background: none; border: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none; border: none;
            }
            QPushButton, QToolButton, QCheckBox, QSlider { cursor: pointer; }
            QWidget#containerSelectAll {
                background: transparent;
                background-color: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
            QLabel#select_all_lbl {
                background: transparent;
                background-color: transparent;
                border: none;
                color: #94A3B8;
                font-size: 11px;
            }
"""

LIGHT_STYLESHEET_OVERRIDES = r"""                QMainWindow, QWidget { background: #F3F5F7; color: #20252B; }
                QFrame#topNav { background: transparent; border-bottom: 1px solid #D9DEE4; }
                QLabel#brand { color: #1D2329; }
                QLabel#version { color: #7A838D; }
                QLabel#themeLabel { color: #68737E; }
                QPushButton#menuButton, QPushButton#navIcon, QPushButton#transport, QPushButton#speedButton {
                    color: #475569; background: transparent; border: 0; border-radius: 6px;
                }
                QPushButton#menuButton:hover, QPushButton#navIcon:hover, QPushButton#transport:hover, QPushButton#speedButton:hover {
                    background: #E2E8F0; color: #2563EB;
                }
                QPushButton#plotTool, QPushButton#plotMaximize {
                    background: transparent; border: 0; color: #475569; border-radius: 5px; font-size: 15px; padding: 3px; outline: none;
                }
                QPushButton#plotTool:hover, QPushButton#plotMaximize:hover {
                    background: #E2E8F0; color: #2563EB;
                }
                QPushButton#plotClose {
                    background: transparent; border: 0; color: #64748B; border-radius: 5px; font-size: 11px; font-weight: bold; padding: 3px; outline: none;
                }
                QPushButton#plotClose:hover {
                    background: #FEE2E2; color: #DC2626;
                }
                QSplitter#dashboardSplitter::handle:horizontal {
                    background: #E2E8F0; width: 6px; margin: 0px 1px; border-radius: 3px;
                }
                QSplitter#dashboardSplitter::handle:horizontal:hover {
                    background: #2563EB;
                }
                QSplitter#stackSplitter::handle:vertical {
                    background: #E2E8F0; height: 6px; margin: 1px 0px; border-radius: 3px;
                }
                QSplitter#stackSplitter::handle:vertical:hover {
                    background: #2563EB;
                }
                QPushButton#plotTool:disabled { color: #94A3B8; background: transparent; }
                QPushButton#btn_sync {
                    background: #F1F5F9;
                    border: 1px solid #CBD5E1;
                    color: #475569;
                    border-radius: 5px;
                    min-width: 26px;
                    max-width: 26px;
                    min-height: 26px;
                    max-height: 26px;
                    padding: 0px;
                }
                QPushButton#btn_sync:hover {
                    background: #E2E8F0;
                    color: #1E293B;
                    border-color: #94A3B8;
                }
                QPushButton#btn_sync:checked {
                    background: #2563EB;
                    color: #FFFFFF;
                    border-color: #1D4ED8;
                }
                QFrame#sidebar { background: #F7F9FB; border-right: 1px solid #D9DEE4; }
                QLabel#sidebarTitle, QLabel#eyebrow { color: #606A74; }
                QListWidget { color: #4D5761; background: transparent; border: 0; outline: 0; }
                QListWidget::item { background: transparent; border: none; padding: 0; margin: 2px 0; }
                QListWidget::item:hover { background: transparent; }
                QListWidget::item:selected { background: transparent; }
                QScrollBar:vertical {
                    background: transparent;
                    width: 10px;
                    margin: 4px 2px 4px 2px;
                    border-radius: 5px;
                    border: none;
                }
                QScrollBar::track:vertical {
                    background-color: #E2E8F0;
                    border-radius: 5px;
                    border: none;
                }
                QScrollBar::handle:vertical {
                    background-color: #94A3B8;
                    min-height: 28px;
                    border-radius: 5px;
                    border: none;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: #64748B;
                }
                QScrollBar::handle:vertical:pressed {
                    background-color: #475569;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px; width: 0px; background: none; border: none;
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: none; border: none;
                }
                QFrame#audioFileCard {
                    background: #FFFFFF;
                    border: 1px solid #D9DEE4;
                    border-radius: 6px;
                }
                QFrame#audioFileCard:hover {
                    background: #F1F5F9;
                    border-color: #CBD5E1;
                }
                QFrame#audioFileCard[active="true"] {
                    background: #DCEFFF;
                    border: 1px solid #2E8ED8;
                }
                QLabel#audioFileName {
                    color: #334155;
                    font-size: 12px;
                    font-weight: 500;
                }
                QFrame#audioFileCard[active="true"] QLabel#audioFileName {
                    color: #164D78;
                    font-weight: 600;
                }
                QFrame#summaryCard, QFrame#transportTimelineCard, QFrame#timelineCard {
                    background: #FFFFFF; border: 1px solid #D9DEE4;
                    border-radius: 10px;
                }
                QScrollBar:horizontal {
                    height: 0px;
                    width: 0px;
                    background: transparent;
                    border: none;
                }
                QScrollBar:vertical {
                    background: transparent;
                    width: 6px;
                    margin: 0px;
                }
                QScrollBar::handle:vertical {
                    background: #CBD5E1;
                    min-height: 20px;
                    border-radius: 3px;
                }
                QScrollBar::handle:vertical:hover {
                    background: #94A3B8;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: transparent;
                    border: none;
                    height: 0px;
                }
                QFrame#plotCard, QWidget#plotCard {
                    background: #FFFFFF;
                    border: 1px solid #CBD5E1;
                    border-radius: 14px;
                }
                QFrame#plotCard:hover, QWidget#plotCard:hover {
                    border-color: #94A3B8;
                }
                QFrame#plotCard[mainPlot="true"], QWidget#plotCard[mainPlot="true"] {
                    border: 1.5px solid #2563EB;
                    border-radius: 14px;
                }
                QWidget#plotTitleBar {
                    background: #F1F5F9;
                    border: 0;
                    border-bottom: 1px solid #E2E8F0;
                    border-top-left-radius: 13px;
                    border-top-right-radius: 13px;
                }
                QLabel#plotTitle {
                    color: #1E293B;
                    font-size: 11.5px;
                    font-weight: 600;
                }
                QFrame#playbackCard, QWidget#playCenter, QWidget#volumeCluster, QLabel#elapsedLabel, QLabel#volumeLabel {
                    background-color: transparent;
                    background: transparent;
                    border: 0;
                }
                QLabel#summaryFile, QLabel#metricValue { color: #1D2329; }
                QLabel#summaryMeta, QLabel#metricTitle, QLabel#metricSub, QLabel#volumeLabel, QLabel#elapsedLabel { color: #69737D; }
                /* Ação Primária do Cabeçalho (Reanalisar) */
                QPushButton#summaryPrimaryAction {
                    background-color: #2563EB;
                    color: #FFFFFF;
                    border: 1px solid #2563EB;
                    border-radius: 5px;
                    min-height: 18px;
                    max-height: 18px;
                    padding: 4px 12px;
                    font-size: 12px;
                    font-weight: 600;
                    outline: none;
                }
                QPushButton#summaryPrimaryAction:hover {
                    background-color: #1D4ED8;
                    border-color: #1D4ED8;
                }
                QPushButton#summaryPrimaryAction:pressed {
                    background-color: #1E40AF;
                    border-color: #1E40AF;
                }

                /* Alternância de Inteligência Artificial (Pill Toggle) */
                QPushButton#summaryToggleMl {
                    min-height: 18px;
                    max-height: 18px;
                    border-radius: 14px;
                    padding: 4px 12px;
                    font-size: 11.5px;
                    font-weight: 600;
                    outline: none;
                }
                QPushButton#summaryToggleMl[active="true"] {
                    background-color: #ECFDF5;
                    border: 1px solid #059669;
                    color: #065F46;
                }
                QPushButton#summaryToggleMl[active="true"]:hover {
                    background-color: #D1FAE5;
                    border-color: #047857;
                    color: #064E3B;
                }
                QPushButton#summaryToggleMl[active="false"] {
                    background-color: #F1F5F9;
                    border: 1px solid #CBD5E1;
                    color: #64748B;
                }
                QPushButton#summaryToggleMl[active="false"]:hover {
                    background-color: #E2E8F0;
                    border-color: #94A3B8;
                    color: #334155;
                }

                /* Ações Secundárias do Cabeçalho */
                QPushButton#summaryAction, QPushButton.summarySecondaryAction {
                    background-color: #F1F5F9;
                    color: #334155;
                    border: 1px solid #CBD5E1;
                    border-radius: 5px;
                    min-height: 18px;
                    max-height: 18px;
                    padding: 4px 10px;
                    font-size: 12px;
                    font-weight: 500;
                    outline: none;
                }
                QPushButton#summaryAction:hover, QPushButton.summarySecondaryAction:hover {
                    background-color: #E2E8F0;
                    border-color: #94A3B8;
                    color: #0F172A;
                }
                QPushButton#summaryAction:pressed, QPushButton.summarySecondaryAction:pressed {
                    background-color: #CBD5E1;
                    border-color: #64748B;
                }
                QPushButton#summaryAction:disabled, QPushButton.summarySecondaryAction:disabled {
                    background-color: #F8FAFC;
                    color: #94A3B8;
                    border-color: #E2E8F0;
                }

                /* Slider Vertical do Eixo Y do Espectrograma */
                QSlider#specYSlider {
                    background: transparent;
                    border: none;
                    width: 16px;
                    margin: 4px 0px;
                }
                QSlider#specYSlider::groove:vertical {
                    width: 3px;
                    background: #E2E8F0;
                    border: none;
                    border-radius: 1.5px;
                }
                QSlider#specYSlider::sub-page:vertical {
                    background: #E2E8F0;
                    border-radius: 1.5px;
                }
                QSlider#specYSlider::add-page:vertical {
                    background: #2563EB;
                    border-radius: 1.5px;
                }
                QSlider#specYSlider::handle:vertical {
                    background: #2563EB;
                    border: 1px solid #1D4ED8;
                    width: 10px;
                    height: 10px;
                    margin: 0 -3.5px;
                    border-radius: 5px;
                }
                QSlider#specYSlider::handle:vertical:hover {
                    background: #3B82F6;
                    border: 1px solid #2563EB;
                }
                QSlider#volumeSlider::groove:horizontal { background: #CFD6DD; }
                QSlider#volumeSlider::sub-page:horizontal { background: #3C93D8; }
                QSlider#volumeSlider::handle:horizontal { background: #FFFFFF; border: 1px solid #B9C3CC; }
                QPushButton#playButton { background: #2E8ED8; color: #FFFFFF; outline: none; border: 0; }
                QPushButton#playButton:hover { background: #3B9BE7; }
                QPushButton#playButton:focus { outline: none; border: 0; }
                QMenu {
                    background-color: #FFFFFF;
                    color: #1E293B;
                    border: 1px solid #CBD5E1;
                    border-radius: 8px;
                    padding: 6px;
                }
                QMenu::item {
                    padding: 8px 26px 8px 12px;
                    border-radius: 6px;
                    margin: 2px 2px;
                    background-color: transparent;
                    color: #1E293B;
                    font-size: 12px;
                }
                QMenu::item:selected {
                    background-color: #2563EB;
                    color: #FFFFFF;
                    font-weight: 600;
                }
                QMenu::item:pressed {
                    background-color: #1D4ED8;
                    color: #FFFFFF;
                }
                QMenu::separator {
                    height: 1px;
                    background-color: #E2E8F0;
                    margin: 5px 6px;
                }
                QMenu::right-arrow {
                    margin-right: 8px;
                }
                QCheckBox { spacing: 6px; color: #374151; background: transparent; }
                QCheckBox::indicator { width: 14px; height: 14px; border-radius: 3px; border: 1px solid #9CA3AF; background-color: #FFFFFF; }
                QToolTip { background: #FFFFFF; color: #27313A; border-color: #CDD4DB; }
                QPushButton, QToolButton, QCheckBox, QSlider { cursor: pointer; }
                QWidget#containerSelectAll {
                    background: transparent;
                    background-color: transparent;
                    border: none;
                    margin: 0px;
                    padding: 0px;
                }
                QLabel#select_all_lbl {
                    background: transparent;
                    background-color: transparent;
                    border: none;
                    color: #64748B;
                    font-size: 11px;
                }
"""

def get_modern_stylesheet(theme_mode="dark"):
    """Retorna a folha de estilo completa para o tema solicitado ('dark' ou 'light')."""
    if theme_mode == "light":
        return DARK_STYLESHEET + "\n" + LIGHT_STYLESHEET_OVERRIDES
    return DARK_STYLESHEET
