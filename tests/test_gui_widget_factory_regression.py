import unittest

import tategakiXTC_gui_widget_factory as gui_widget_factory


class _SignalStub:
    def __init__(self):
        self.connected = []

    def connect(self, callback):
        self.connected.append(callback)


class _ButtonStub:
    def __init__(self, text=''):
        self.text = text
        self.object_name = ''
        self.tooltip = ''
        self.fixed_width = None
        self.minimum_width = None
        self.fixed_size = None
        self.checkable = False
        self.checked = False
        self.enabled = True
        self.focus_policy = None
        self.properties = {}
        self.clicked = _SignalStub()

    def setText(self, text):
        self.text = text

    def setObjectName(self, value):
        self.object_name = value

    def setToolTip(self, value):
        self.tooltip = value

    def setFixedSize(self, width, height):
        self.fixed_size = (width, height)

    def setFixedWidth(self, value):
        self.fixed_width = value

    def setMinimumWidth(self, value):
        self.minimum_width = value

    def setCheckable(self, value):
        self.checkable = bool(value)

    def setChecked(self, value):
        self.checked = bool(value)

    def setEnabled(self, value):
        self.enabled = bool(value)

    def setFocusPolicy(self, value):
        self.focus_policy = value

    def setProperty(self, name, value):
        self.properties[name] = value


class _LayoutStub:
    def __init__(self):
        self.spacing = None
        self.contents_margins = None
        self.operations = []

    def setSpacing(self, value):
        self.spacing = value

    def setContentsMargins(self, left, top, right, bottom):
        self.contents_margins = (left, top, right, bottom)

    def addStretch(self, value):
        self.operations.append(('stretch', value))

    def addSpacing(self, value):
        self.operations.append(('spacing', value))

    def addWidget(self, widget):
        self.operations.append(('widget', widget))


class _LabelStub:
    def __init__(self, text=''):
        self.text = text
        self.object_name = ''
        self.word_wrap = False

    def setObjectName(self, value):
        self.object_name = value

    def setWordWrap(self, value):
        self.word_wrap = bool(value)


class _GroupBoxStub:
    def __init__(self, title=''):
        self.title = title
        self.object_name = ''
        self.layout = None

    def setObjectName(self, value):
        self.object_name = value

    def setLayout(self, layout):
        self.layout = layout


class _NoSetLayoutGroupBoxStub:
    def __init__(self, title=''):
        self.title = title
        self.object_name = ''
        self.layout = None

    def setObjectName(self, value):
        self.object_name = value


class _WidgetStub:
    pass


class _ParentAwareLayoutStub(_LayoutStub):
    def __init__(self):
        super().__init__()
        self.parent = None

    def setParent(self, parent):
        self.parent = parent


class _ParentRejectingLayoutStub(_ParentAwareLayoutStub):
    def __init__(self, parent=None):
        if parent is not None:
            raise TypeError('parent not supported')
        super().__init__()



class GuiWidgetFactoryRegressionTests(unittest.TestCase):
    def test_apply_button_widget_plan_applies_text_size_flags_and_focus(self):
        button = _ButtonStub('old')
        plan = {
            'text': '  開く  ',
            'object_name': '  openBtn  ',
            'tooltip': '  フォルダを開く  ',
            'fixed_width': 84,
            'minimum_width': 96,
            'checkable': True,
            'checked': True,
            'enabled': False,
            'focus_policy': 'no_focus',
        }

        result = gui_widget_factory.apply_button_widget_plan(button, plan, no_focus_policy='NO_FOCUS')

        self.assertIs(result, button)
        self.assertEqual(button.text, '開く')
        self.assertEqual(button.object_name, 'openBtn')
        self.assertEqual(button.tooltip, 'フォルダを開く')
        self.assertEqual(button.fixed_width, 84)
        self.assertEqual(button.minimum_width, 96)
        self.assertTrue(button.checkable)
        self.assertTrue(button.checked)
        self.assertFalse(button.enabled)
        self.assertEqual(button.focus_policy, 'NO_FOCUS')

    def test_make_button_from_plan_connects_clicked_callback(self):
        received = []

        def on_click():
            received.append('clicked')

        button = gui_widget_factory.make_button_from_plan(
            {'text': '更新', 'fixed_size': (36, 24)},
            clicked=on_click,
            button_factory=_ButtonStub,
            no_focus_policy='NO_FOCUS',
        )

        self.assertEqual(button.text, '更新')
        self.assertEqual(button.fixed_size, (36, 24))
        self.assertEqual(button.clicked.connected, [on_click])
        button.clicked.connected[0]()
        self.assertEqual(received, ['clicked'])

    def test_apply_button_widget_plan_skips_minimum_width_when_fixed_size_is_present(self):
        button = _ButtonStub('old')

        result = gui_widget_factory.apply_button_widget_plan(
            button,
            {'text': '保持', 'fixed_size': (36, 24), 'minimum_width': 120},
            no_focus_policy='NO_FOCUS',
        )

        self.assertIs(result, button)
        self.assertEqual(button.fixed_size, (36, 24))
        self.assertIsNone(button.minimum_width)

    def test_apply_button_widget_plan_can_clear_existing_text_tooltip_and_checkable_state(self):
        button = _ButtonStub('old')
        button.object_name = 'legacyBtn'
        button.tooltip = 'legacy tip'
        button.checkable = True
        button.checked = True

        result = gui_widget_factory.apply_button_widget_plan(
            button,
            {'text': ' ', 'object_name': ' ', 'tooltip': ' ', 'checkable': False, 'enabled': True},
            no_focus_policy='NO_FOCUS',
        )

        self.assertIs(result, button)
        self.assertEqual(button.text, '')
        self.assertEqual(button.object_name, '')
        self.assertEqual(button.tooltip, '')
        self.assertFalse(button.checkable)
        self.assertFalse(button.checked)
        self.assertTrue(button.enabled)

    def test_make_hbox_layout_from_plan_applies_spacing_margins_and_optional_stretch(self):
        layout = gui_widget_factory.make_hbox_layout_from_plan(
            {'spacing': 8, 'contents_margins': (1, 2, 3, 4), 'add_stretch': True},
            layout_factory=_LayoutStub,
        )

        self.assertEqual(layout.spacing, 8)
        self.assertEqual(layout.contents_margins, (1, 2, 3, 4))
        self.assertEqual(layout.operations, [('stretch', 1)])

    def test_apply_button_widget_plan_normalizes_boolean_like_and_numeric_like_values(self):
        button = _ButtonStub('old')

        result = gui_widget_factory.apply_button_widget_plan(
            button,
            {
                'fixed_width': '84',
                'minimum_width': '96',
                'checkable': 'true',
                'checked': 'false',
                'enabled': '0',
            },
            no_focus_policy='NO_FOCUS',
        )

        self.assertIs(result, button)
        self.assertEqual(button.fixed_width, 84)
        self.assertEqual(button.minimum_width, 96)
        self.assertTrue(button.checkable)
        self.assertFalse(button.checked)
        self.assertFalse(button.enabled)

    def test_make_layout_from_plan_ignores_non_mapping_and_invalid_values_without_crashing(self):
        hbox = gui_widget_factory.make_hbox_layout_from_plan(
            'bad-plan',
            default_spacing=5,
            default_margins=(9, 8, 7, 6),
            layout_factory=_LayoutStub,
        )
        vbox = gui_widget_factory.make_vbox_layout_from_plan(
            {'spacing': 'bad-spacing', 'contents_margins': ('1', 'bad', 3), 'add_stretch': 'false'},
            default_spacing=4,
            default_margins=(1, 2, 3, 4),
            layout_factory=_LayoutStub,
        )

        self.assertEqual(hbox.spacing, 5)
        self.assertEqual(hbox.contents_margins, (9, 8, 7, 6))
        self.assertEqual(hbox.operations, [])
        self.assertEqual(vbox.spacing, 4)
        self.assertEqual(vbox.contents_margins, (1, 2, 3, 4))
        self.assertEqual(vbox.operations, [])

    def test_build_labeled_widget_row_creates_labels_pair_spacing_and_trailing_stretch(self):
        widget_a = _WidgetStub()
        widget_b = _WidgetStub()
        row = gui_widget_factory.build_labeled_widget_row(
            [('  本文  ', widget_a), ('ルビ', widget_b)],
            spacing=5,
            pair_spacing=12,
            label_object_name='customLabel',
            trailing_stretch=True,
            layout_factory=_LayoutStub,
            label_factory=_LabelStub,
        )

        self.assertEqual(row.spacing, 5)
        self.assertEqual(row.contents_margins, (0, 0, 0, 0))
        self.assertEqual(row.operations[0][0], 'widget')
        first_label = row.operations[0][1]
        self.assertIsInstance(first_label, _LabelStub)
        self.assertEqual(first_label.text, '本文')
        self.assertEqual(first_label.object_name, 'customLabel')
        self.assertEqual(row.operations[1], ('widget', widget_a))
        self.assertEqual(row.operations[2], ('spacing', 12))
        second_label = row.operations[3][1]
        self.assertEqual(second_label.text, 'ルビ')
        self.assertEqual(row.operations[4], ('widget', widget_b))
        self.assertEqual(row.operations[-1], ('stretch', 1))

    def test_make_section_and_note_label_use_expected_object_names(self):
        section = gui_widget_factory.make_section('  プリセット  ', group_box_factory=_GroupBoxStub)
        dim_label = gui_widget_factory.make_dim_label('機種', label_factory=_LabelStub)
        note_label = gui_widget_factory.make_note_label('説明', label_factory=_LabelStub)

        self.assertEqual(section.title, 'プリセット')
        self.assertEqual(section.object_name, 'settingsSection')
        self.assertEqual(dim_label.object_name, 'dimLabel')
        self.assertEqual(note_label.object_name, 'subNoteLabel')
        self.assertTrue(note_label.word_wrap)


    def test_make_vbox_section_layout_and_help_button_share_widget_factory_rules(self):
        box, layout, plan = gui_widget_factory.make_section_box_layout(
            '  表示と実機  ',
            {'title': '  表示と実機  ', 'contents_margins': (4, 5, 6, 7), 'spacing': 9},
            group_box_factory=_GroupBoxStub,
            layout_factory=_LayoutStub,
        )

        received = []
        button = gui_widget_factory.make_help_icon_button(
            '説明文',
            clicked_with_button=lambda btn: received.append(btn.properties.get('helpText')),
            button_factory=_ButtonStub,
            no_focus_policy='NO_FOCUS',
        )

        self.assertEqual(box.title, '表示と実機')
        self.assertIs(box.layout, layout)
        self.assertEqual(layout.spacing, 9)
        self.assertEqual(layout.contents_margins, (4, 5, 6, 7))
        self.assertEqual(plan['title'], '  表示と実機  ')
        self.assertEqual(button.text, '?')
        self.assertEqual(button.object_name, 'miniHelpBtn')
        self.assertEqual(button.fixed_size, (20, 20))
        self.assertEqual(button.tooltip, '説明文')
        self.assertEqual(button.properties['helpText'], '説明文')
        self.assertEqual(button.focus_policy, 'NO_FOCUS')
        self.assertEqual(len(button.clicked.connected), 1)
        button.clicked.connected[0]()
        self.assertEqual(received, ['説明文'])

    def test_make_section_box_layout_preserves_layout_attachment_when_parent_ctor_rejects_box(self):
        box, layout, _plan = gui_widget_factory.make_section_box_layout(
            '画像処理',
            {'title': '画像処理', 'contents_margins': (1, 2, 3, 4), 'spacing': 7},
            group_box_factory=_NoSetLayoutGroupBoxStub,
            layout_factory=_ParentRejectingLayoutStub,
        )

        self.assertIs(layout.parent, box)
        self.assertEqual(layout.spacing, 7)
        self.assertEqual(layout.contents_margins, (1, 2, 3, 4))


    def test_make_section_box_layout_ignores_non_mapping_plan_without_crashing(self):
        box, layout, plan = gui_widget_factory.make_section_box_layout(
            '画像処理',
            'bad-plan',
            group_box_factory=_GroupBoxStub,
            layout_factory=_LayoutStub,
        )

        self.assertEqual(box.title, '画像処理')
        self.assertEqual(layout.spacing, 6)
        self.assertEqual(layout.contents_margins, (8, 8, 8, 8))
        self.assertIsInstance(plan, dict)


if __name__ == '__main__':
    unittest.main()
