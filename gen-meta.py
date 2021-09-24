import os
from clang.cindex import *

#
# UTILS
#

def has_child(node, kind, spel = ''):
  for child in node.get_children():
    if child.kind == kind and child.spelling == spel:
      return True
  return False

def has_child_any(node, kind, spels):
  for spel in spels:
    if has_child(node, kind, spel):
      return True
  return False

def has_base_spec(node, spec):
  for child in node.get_children():
    if child.kind == CursorKind.CXX_BASE_SPECIFIER:
      if has_child(child, CursorKind.TYPE_REF, spec):
        return True
  return False

def join_namespace(a, b):
  if len(a) == 0:
    return b
  return a + '::' + b

def enum_namespace(node, name, full):
  if node.kind != CursorKind.NAMESPACE:
    return []
  if node.spelling == name:
    return [[node, full]]
  x = []
  for child in node.get_children():
    x += enum_namespace(
      child, name,
      join_namespace(full, node.spelling))
  return x

def get_namespaces(node, name, full = ''):
  x = []
  if node.kind == CursorKind.NAMESPACE:
    x += enum_namespace(node, name, full)
  else:
    for child in node.get_children():
      x += get_namespaces(child, name)
  return x

def is_punct(spel):
  puncts = [
    '(', ')', '[', ']', '{', '}', '<', '>', ';', ',', '::', ':'
  ]
  return spel in puncts

def need_space(a, b):
  if a == ':':
    return True
  return (not is_punct(a)) and (not is_punct(b))

def get_endl(node):
  if node.kind == CursorKind.NAMESPACE:
    return ''
  return ';'

def tokens_of(node):
  decl = ''
  prev = ''
  for token in node.get_tokens():
    curr = token.spelling
    if len(decl) > 0 and need_space(prev, curr):
      decl += ' '
    decl += curr
    prev = curr
  return decl + get_endl(node)

def print_tree(node, s = ''):
  print(s + str(node.kind))
  if len(node.spelling) > 0:
    print(s + node.spelling)
  for child in node.get_children():
    print_tree(child, s + '  ')

#
# CODEGEN
#

tag_entity = 'struct laplace::__gen::entity'
tag_real   = 'struct laplace::__gen::real'
tag_points = 'struct laplace::__gen::points'

def print_access(node, s = ''):
  if node.kind == CursorKind.STRUCT_DECL:
    print(s + 'public:')
  elif node.kind == CursorKind.CLASS_DECL:
    print(s + 'private:')

def has_meta_tag(node):
  return has_child_any(
    node, CursorKind.TYPE_REF,
    [tag_entity, tag_real, tag_points])

def gen_meta_tag(node, s = ''):
  if has_child(node, CursorKind.TYPE_REF, tag_real):
    print(s + 'private:')
    print(s + '  sl::index n_' + node.spelling + ' = {};\n')
    print(s + 'public:')
    print(s + '  static void set_' + node.spelling + '(entity en, intval value) noexcept;')
    print(s + '  [[nodiscard]] static auto get_' + node.spelling + '(entity en) noexcept -> intval;')
    print(s + '  [[nodiscard]] static auto scale_of_' + node.spelling + '(entity en) noexcept -> intval;\n')

def print_helpers(s = ''):
  print(s + 'public:')
  print(s + '  using entity = laplace::engine::access::entity const &;\n')

def gen_meta_tags(node, s = ''):
  for child in node.get_children():
    if has_meta_tag(child):
      gen_meta_tag(child, s)

def print_without_meta_tags(node, s = ''):
  for child in node.get_children():
    if not has_meta_tag(child):
      print(s + tokens_of(child))

def gen_entity(node, s = ''):
  print(s + '/* Generated entity.')
  print(s + ' */')
  print(s + 'class ' + node.spelling + ' : public laplace::engine::basic_entity {')
  print_helpers(s);
  gen_meta_tags(node, s)
  print_access(node, s);
  print_without_meta_tags(node, s + '  ');
  print(s + '};')

def print_without_using(node, tag, s = ''):
  if has_child(node, CursorKind.NAMESPACE_REF, tag):
    print(s + '/* ' + tokens_of(node) + ' */\n')
  else:
    print(s + tokens_of(node) + '\n')

def modify_node(node, s = ''):
  if has_base_spec(node, tag_entity):
    gen_entity(node, s)
  else:
    print_without_using(node, '__gen', s)

def modify_namespace(node, name, s = ''):
  print(s + '/**')
  print(s + ' * AST')
  print(s + ' *')
  print_tree(node, s)
  print(s + ' */\n')

  print(s + 'namespace ' + name + ' {')
  print(s + '  using laplace::engine::intval;\n')

  for child in node.get_children():
    modify_node(child, s + '  ')

  print(s + '}')

def process(node):
  namespaces = get_namespaces(node, '__meta')
  for x in namespaces:
    modify_namespace(x[0], x[1])

def main():
  if 'CLANG_LIBRARY_PATH' in os.environ:
    Config.set_library_path(os.environ['CLANG_LIBRARY_PATH'])

  index = None

  try:
    index = Index.create()

  except:
    print(
      'Set CLANG_LIBRARY_PATH environment variable to your <LLVM>/bin folder.')
    return

  u = index.parse('__source.cpp', unsaved_files=[
    ('__source.cpp', '#include "unit.in.h"\n')
  ])

  process(u.cursor)

if __name__ == '__main__':
  main()
