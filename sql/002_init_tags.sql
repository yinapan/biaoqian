-- sql/002_init_tags.sql

-- ===== 模型模块 (module_type=1) 标签维度 =====
INSERT INTO tag_definitions (module_type, field_name, display_name, field_type, is_fixed, sort_order) VALUES
(1, 'species',       '物种', 'enum_single', true,  1),
(1, 'gender',        '性别', 'enum_single', true,  2),
(1, 'region',        '地域', 'enum_multi',  true,  3),
(1, 'faction',       '势力', 'enum_multi',  true,  4),
(1, 'profession',    '职业', 'enum_multi',  true,  5),
(1, 'body_type',     '体型', 'enum_single', true,  6),
(1, 'age_group',     '年龄', 'enum_single', true,  7),
(1, 'clothing',      '衣着', 'enum_multi',  true,  8),
(1, 'features',      '特征', 'enum_multi',  false, 9),
(1, 'exclusive_npc', '专属NPC', 'text',     false, 10);

-- 模型标签值（已知固定值）
INSERT INTO tag_values (definition_id, value, sort_order)
SELECT id, v, ord FROM tag_definitions td,
  unnest(ARRAY['人','老虎','狮子','狼','马','牛','熊','鸟','鹿','龙','虫','鱼']) WITH ORDINALITY AS t(v, ord)
WHERE td.module_type = 1 AND td.field_name = 'species';

INSERT INTO tag_values (definition_id, value, sort_order)
SELECT id, v, ord FROM tag_definitions td,
  unnest(ARRAY['男','女']) WITH ORDINALITY AS t(v, ord)
WHERE td.module_type = 1 AND td.field_name = 'gender';

INSERT INTO tag_values (definition_id, value, sort_order)
SELECT id, v, ord FROM tag_definitions td,
  unnest(ARRAY['标准','壮硕','瘦子','胖子','侏儒','异种']) WITH ORDINALITY AS t(v, ord)
WHERE td.module_type = 1 AND td.field_name = 'body_type';

INSERT INTO tag_values (definition_id, value, sort_order)
SELECT id, v, ord FROM tag_definitions td,
  unnest(ARRAY['小孩','青年','中年','老年']) WITH ORDINALITY AS t(v, ord)
WHERE td.module_type = 1 AND td.field_name = 'age_group';

INSERT INTO tag_values (definition_id, value, sort_order)
SELECT id, v, ord FROM tag_definitions td,
  unnest(ARRAY['护甲','劲装','布衣','华服','冬衣']) WITH ORDINALITY AS t(v, ord)
WHERE td.module_type = 1 AND td.field_name = 'clothing';

-- region/faction/profession/features 值很多，由 tag_initializer.py 从 Excel 枚举行动态提取

-- ===== 动作模块 (module_type=3) 标签维度 =====
INSERT INTO tag_definitions (module_type, field_name, display_name, field_type, is_fixed, is_filterable, is_searchable, sort_order) VALUES
(3, 'body_type',     '体型',     'enum_single',  true,  true,  true,  1),
(3, 'action_module', '动作模组', 'enum_single',  true,  true,  true,  2),
(3, 'action_type',   '动作类型', 'enum_single',  true,  true,  true,  3),
(3, 'action_id',     '动作ID',   'number_range', false, true,  false, 4),
(3, 'remark',        '备注',     'text',         false, false, true,  5),
(3, 'slot_name',     '插槽',     'text',         false, false, false, 6),
(3, 'slot_path',     '插槽路径', 'text',         false, false, false, 7),
(3, 'effect_path',   '特效资源', 'text',         false, false, false, 8);

-- ===== 特效模块 (module_type=2) 标签维度 =====
-- 当前只有 JSON 中的量化字段，语义标签后续由用户手工加到 JSON 后再补充 tag_definitions
INSERT INTO tag_definitions (module_type, field_name, display_name, field_type, is_fixed, is_filterable, is_searchable, sort_order, config) VALUES
(2, 'effect_duration_sec', '特效时长',   'number_range', false, true,  false, 1, '{"min":0,"max":60,"step":0.1,"unit":"s"}'),
(2, 'length_cm',           '长度(cm)',   'number_range', false, true,  false, 2, '{"min":0,"max":50000,"step":100,"unit":"cm"}'),
(2, 'width_cm',            '宽度(cm)',   'number_range', false, true,  false, 3, '{"min":0,"max":50000,"step":100,"unit":"cm"}'),
(2, 'height_cm',           '高度(cm)',   'number_range', false, true,  false, 4, '{"min":0,"max":50000,"step":100,"unit":"cm"}'),
(2, 'source_name',         '资源名',     'text',        false, false, true,  5, '{}');

-- ===== 常用同义词 =====
INSERT INTO tag_synonyms (module_type, field_name, target_value, synonym, priority) VALUES
(1, 'profession', '僧侣', '和尚', 10),
(1, 'profession', '僧侣', '出家人', 10),
(1, 'profession', '侠客', '大侠', 10),
(1, 'body_type',  '壮硕', '壮', 5),
(1, 'body_type',  '瘦子', '瘦', 5),
(1, 'body_type',  '胖子', '胖', 5),
(1, 'gender',     '女', '女性', 5),
(1, 'gender',     '男', '男性', 5),
(1, 'age_group',  '老年', '老人', 5),
(1, 'age_group',  '青年', '年轻', 5),
(1, 'age_group',  '小孩', '儿童', 5);
