import subprocess

import rich.console, argparse, pathlib, ast, sys, os


SCRIPT_NAME = pathlib.Path(__file__).name

con = rich.console.Console()

auto_change_name: dict[str, str] = {
    "print": "println!",
    "str": "String",
    "int": "i64",
    "float": "f64",
    "None": "()"
}

operations = {
    ast.Add: "+",
    ast.Sub: "-",
    ast.Mult: "*",
    ast.Div: "/",
    ast.FloorDiv: "//",
    ast.Mod: "%",
    ast.Pow: "**",
    ast.Lt: "<",
    ast.LtE: "<=",
    ast.Gt: ">",
    ast.GtE: ">=",
    ast.Eq: "==",
    ast.NotEq: "!="
}

if os.name == "nt":
    EXE_EXTENSION = ".exe"
else:
    EXE_EXTENSION = ""

def represent_obj(const: object) -> str:
    match type(const).__name__:
        case "list":
            return f"vec![{", ".join([represent_obj(inner_const) for inner_const in list(const)])}]"
        case "str":
            return "\"" + repr(const)[1:-1].replace("\"", "\\\"",).replace("\\'", "'") + "\""

    return repr(const)

def kwargs_to_dict(kwargs: list[ast.keyword]) -> dict[str, object]:
    kwargs_dict = {}

    for kwarg in kwargs:
        kwargs_dict[kwarg.arg] = kwarg.value

    return kwargs_dict

def infer_type(value_node: ast.Constant) -> str:
    if isinstance(value_node.value, int): return "i64"
    if isinstance(value_node.value, float): return "f64"
    if isinstance(value_node.value, bool): return "bool"
    if isinstance(value_node.value, str): return "&'static str"
    if value_node.value is None: return "()"
    return "i64"

class TranspileError(ValueError): ...

class RustTranspiler:
    @classmethod
    def transpile_Compare(cls, tree: ast.Compare):
        left, right = tree.left, tree.comparators[0]

        return f"{cls.transpile(left)}{operations[type(tree.ops[0])]}{cls.transpile(right)}"

    @classmethod
    def transpile_While(cls, tree: ast.While):
        if isinstance(tree.test, ast.Constant) and tree.test.value:
            return "loop {body}".replace("body", cls.transpile_stmts(tree.body))
        else:
            return (f"while {cls.transpile(tree.test)} [[{cls.transpile_stmts(tree.body)}]]".replace("[[", "{")
                    .replace("]]", "}"))

    @classmethod
    def transpile_BinOp(cls, tree: ast.BinOp) -> str:
        if operations[type(tree.op)] == "*":
            return f"{cls.transpile(tree.left)}.pow({cls.transpile(tree.right)})"

        return f"{cls.transpile(tree.left)}{operations[type(tree.op)]}{cls.transpile(tree.right)}"

    @classmethod
    def transpile_Assign(cls, tree: ast.Assign) -> str:
        return cls.transpile(ast.AnnAssign(
            target=tree.targets[0],
            annotation=ast.Name(tree.value),
            value=tree.value,
            simple=1
        ))

    @classmethod
    def transpile_AnnAssign(cls, tree: ast.AnnAssign) -> str:
        value_name_ast: ast.Name = tree.target
        value_name = value_name_ast.id
        rust_type = cls.transpile(tree.annotation)

        is_const = value_name.isupper()

        if tree.value is None:
            raise TranspileError(f"the variable {tree.value} does not define a value")

        if is_const:
            if isinstance(tree.value, ast.Constant):
                return f"const {tree.target.id} : {rust_type} = {cls.transpile(tree.value)}"
            else:
                return f"static {tree.target.id} : {rust_type} = {cls.transpile(tree.value)}"
        else:
            return f"let mut {tree.target.id} : {rust_type} = {cls.transpile(tree.value)}"

    @classmethod
    def func_println_(cls, tree: ast.Call):
        inners = [cls.transpile(expr) for expr in tree.args]
        kwargs = kwargs_to_dict(tree.keywords)

        sep = str(kwargs.get("sep", " "))
        end = str(kwargs.get("end", "\n"))

        return f"print!(\"{sep.join(["{}" * len(inners)])}{represent_obj(end)[1:-1]}\", {", ".join(inners)})"

    @classmethod
    def transpile_stmts(cls, stmts: list[ast.stmt]) -> str:
        statements: list[str] = []

        for statement in stmts:
            statements.append(cls.transpile(statement))

        return "\n".join([f"{statement};" for statement in statements])

    @classmethod
    def transpile_FunctionDef(cls, tree: ast.FunctionDef) -> str:
        return f"""fn {tree.name}({", ".join([f"{arg.arg}: {cls.transpile(arg.annotation)}" for arg in tree.args.args])})""" + (
        f"{cls.transpile_stmts(tree.body)}")

    @classmethod
    def transpile_Constant(cls, tree: ast.Constant) -> str:
        value = tree.value

        return represent_obj(value)

    @classmethod
    def transpile_Name(cls, tree: ast.Name) -> str:
        return auto_change_name.get(tree.id, tree.id)

    @classmethod
    def transpile_Call(cls, tree: ast.Call) -> str:
        if hasattr(cls, "func_" + cls.transpile(tree.func).replace("!", "_")):
            return getattr(cls, "func_" + cls.transpile(tree.func).replace("!", "_"))(tree)

        return f"{cls.transpile(tree.func)}({",".join([cls.transpile(arg) for arg in tree.args])})"

    @classmethod
    def transpile_Expr(cls, tree: ast.Expr) -> str:
        return cls.transpile(tree.value)

    @classmethod
    def transpile_Module(cls, tree: ast.Module) -> str:
        statements: list[str] = []
        before_main_stmts: list[str] = []

        for statement in tree.body:
            if isinstance(statement, ast.FunctionDef):
                before_main_stmts.append(cls.transpile(statement))
            else:
                statements.append(cls.transpile(statement))

        return "#![allow(unused_mut)]\n\n\n" + "<bfmcontent>\n fn main() { \n<content>\n}".replace("<content>",
            "\n".join([f"{statement};" for statement in statements])).replace("<bfmcontent>",
            "\n".join([f"{statement}" for statement in before_main_stmts]))

    @classmethod
    def transpile(cls, tree: ast.AST) -> str:
        function = getattr(cls, f"transpile_{tree.__class__.__name__}", lambda x: f"/* {repr(x)} */")
import subprocess

import rich.console, argparse, pathlib, ast, sys, os


SCRIPT_NAME = pathlib.Path(__file__).name

con = rich.console.Console()

auto_change_name: dict[str, str] = {
    "print": "println!",
    "str": "String",
    "int": "i64",
    "float": "f64",
    "None": "()"
}

operations = {
    ast.Add: "+",
    ast.Sub: "-",
    ast.Mult: "*",
    ast.Div: "/",
    ast.FloorDiv: "//",
    ast.Mod: "%",
    ast.Pow: "**",
    ast.Lt: "<",
    ast.LtE: "<=",
    ast.Gt: ">",
    ast.GtE: ">=",
    ast.Eq: "==",
    ast.NotEq: "!="
}

if os.name == "nt":
    EXE_EXTENSION = ".exe"
else:
    EXE_EXTENSION = ""

def represent_obj(const: object) -> str:
    match type(const).__name__:
        case "list":
            return f"vec![{", ".join([represent_obj(inner_const) for inner_const in list(const)])}]"
        case "str":
            return "\"" + repr(const)[1:-1].replace("\"", "\\\"",).replace("\\'", "'") + "\""

    return repr(const)

def kwargs_to_dict(kwargs: list[ast.keyword]) -> dict[str, object]:
    kwargs_dict = {}

    for kwarg in kwargs:
        kwargs_dict[kwarg.arg] = kwarg.value

    return kwargs_dict

def infer_type(value_node: ast.Constant) -> str:
    if isinstance(value_node.value, int): return "i64"
    if isinstance(value_node.value, float): return "f64"
    if isinstance(value_node.value, bool): return "bool"
    if isinstance(value_node.value, str): return "&'static str"
    if value_node.value is None: return "()"
    return "i64"

class TranspileError(ValueError): ...

class RustTranspiler:
    @classmethod
    def transpile_Compare(cls, tree: ast.Compare):
        left, right = tree.left, tree.comparators[0]

        return f"{cls.transpile(left)}{operations[type(tree.ops[0])]}{cls.transpile(right)}"

    @classmethod
    def transpile_While(cls, tree: ast.While):
        if isinstance(tree.test, ast.Constant) and tree.test.value:
            return "loop {body}".replace("body", cls.transpile_stmts(tree.body))
        else:
            return (f"while {cls.transpile(tree.test)} [[{cls.transpile_stmts(tree.body)}]]".replace("[[", "{")
                    .replace("]]", "}"))

    @classmethod
    def transpile_BinOp(cls, tree: ast.BinOp) -> str:
        if operations[type(tree.op)] == "*":
            return f"{cls.transpile(tree.left)}.pow({cls.transpile(tree.right)})"

        return f"{cls.transpile(tree.left)}{operations[type(tree.op)]}{cls.transpile(tree.right)}"

    @classmethod
    def transpile_Assign(cls, tree: ast.Assign) -> str:
        return cls.transpile(ast.AnnAssign(
            target=tree.targets[0],
            annotation=ast.Name(tree.value),
            value=tree.value,
            simple=1
        ))

    @classmethod
    def transpile_AnnAssign(cls, tree: ast.AnnAssign) -> str:
        value_name_ast: ast.Name = tree.target
        value_name = value_name_ast.id
        rust_type = cls.transpile(tree.annotation)

        is_const = value_name.isupper()

        if tree.value is None:
            raise TranspileError(f"the variable {tree.value} does not define a value")

        if is_const:
            if isinstance(tree.value, ast.Constant):
                return f"const {tree.target.id} : {rust_type} = {cls.transpile(tree.value)}"
            else:
                return f"static {tree.target.id} : {rust_type} = {cls.transpile(tree.value)}"
        else:
            return f"let mut {tree.target.id} : {rust_type} = {cls.transpile(tree.value)}"

    @classmethod
    def func_println_(cls, tree: ast.Call):
        inners = [cls.transpile(expr) for expr in tree.args]
        kwargs = kwargs_to_dict(tree.keywords)

        sep = str(kwargs.get("sep", " "))
        end = str(kwargs.get("end", "\n"))

        return f"print!(\"{sep.join(["{}" * len(inners)])}{represent_obj(end)[1:-1]}\", {", ".join(inners)})"

    @classmethod
    def transpile_stmts(cls, stmts: list[ast.stmt]) -> str:
        statements: list[str] = []

        for statement in stmts:
            statements.append(cls.transpile(statement))

        return "\n".join([f"{statement};" for statement in statements])

    @classmethod
    def transpile_FunctionDef(cls, tree: ast.FunctionDef) -> str:
        return f"""fn {tree.name}({", ".join([f"{arg.arg}: {cls.transpile(arg.annotation)}" for arg in tree.args.args])})""" + (
        f"{cls.transpile_stmts(tree.body)}")

    @classmethod
    def transpile_Constant(cls, tree: ast.Constant) -> str:
        value = tree.value

        return represent_obj(value)

    @classmethod
    def transpile_Name(cls, tree: ast.Name) -> str:
        return auto_change_name.get(tree.id, tree.id)

    @classmethod
    def transpile_Call(cls, tree: ast.Call) -> str:
        if hasattr(cls, "func_" + cls.transpile(tree.func).replace("!", "_")):
            return getattr(cls, "func_" + cls.transpile(tree.func).replace("!", "_"))(tree)

        return f"{cls.transpile(tree.func)}({",".join([cls.transpile(arg) for arg in tree.args])})"

    @classmethod
    def transpile_Expr(cls, tree: ast.Expr) -> str:
        return cls.transpile(tree.value)

    @classmethod
    def transpile_Module(cls, tree: ast.Module) -> str:
        statements: list[str] = []
        before_main_stmts: list[str] = []

        for statement in tree.body:
            if isinstance(statement, ast.FunctionDef):
                before_main_stmts.append(cls.transpile(statement))
            else:
                statements.append(cls.transpile(statement))

        return "#![allow(unused_mut)]\n\n\n" + "<bfmcontent>\n fn main() { \n<content>\n}".replace("<content>",
            "\n".join([f"{statement};" for statement in statements])).replace("<bfmcontent>",
            "\n".join([f"{statement}" for statement in before_main_stmts]))

    @classmethod
    def transpile(cls, tree: ast.AST) -> str:
        function = getattr(cls, f"transpile_{tree.__class__.__name__}", lambda x: f"/* {repr(x)} */")

        return function(tree)

def generate_arguments() -> argparse.Namespace:
    argument_parser = argparse.ArgumentParser(usage=f"python {SCRIPT_NAME} <options> <file>",
                                              description="Python-To-Rust transpiler and compiler")

    argument_parser.add_argument("file", type=str, help="input python file")
    argument_parser.add_argument("-r", "--rout", "--output-rust", required=False, type=str, help="output Rust file")
    argument_parser.add_argument("-o", "--output", "--output-exe", required=False, type=str, help="output executable file")
    argument_parser.add_argument("-C", "--compile", action="store_true", default=False, help="generate an executable file")
    argument_parser.add_argument("-E", "--execute", action="store_true", default=False,
                                 help="execute the produced executable if any")
    argument_parser.add_argument("-c", "--clean", action="store_true", default=False, help="delete intermediate files")
    argument_parser.add_argument("-S", "--style",  action="store_true", default=False, help="automatically style/format produced rust files")

    args = argument_parser.parse_args()

    return args

def real_transpile(tree: ast.Module) -> str:
    return RustTranspiler.transpile(tree)

def transpile(file: str, rout: str | None = None, output: str | None = None, compile: bool = True, clean: bool = True,
              execute: bool = False, style: bool = False) -> int:
    filepath = pathlib.Path(file)

    if not filepath.exists():
        con.log(f"\"{file}\": does not exist")
        return 1
    elif not filepath.is_file():
        con.log(f"\"{file}\": is not a file")

    try:
        content = filepath.read_text(encoding="utf-8")
    except PermissionError:
        con.log(f"\"{file}\": not enough permission to access")
        return 1
    except UnicodeDecodeError:
        con.log(f"\"{file}\": encoding error (utf-8)")
        return 1
    except OSError as e:
        con.log(f"\"{file}\": not accessible; {" ".join(e.args)}")
        return 1

    try:
        parsed = ast.parse(content, str(filepath.relative_to(".")), "exec", type_comments=True, optimize=2)
    except SyntaxError as e:
        con.log(f"\"{file}\": syntax error at line {e.lineno}, run with Python to get more information")
        return 1

    transpiled = real_transpile(parsed)
    *parts, _ = filepath.name.split(".")
    filepath_no_ext = ".".join(parts)
    rustfile = rout or pathlib.Path(f"/tmp/rustpy_{filepath_no_ext}.rs")  # do windows stuff here eventually
    output = output or f"{filepath_no_ext}{EXE_EXTENSION}"

    with open(rustfile, "w") as f:
        f.write(transpiled)

    if style:
        subprocess.run([f"rustfmt {rustfile}"], shell=True)

    if compile:
        try: os.remove(output)
        except FileNotFoundError: pass

        subprocess.run([f"rustc {rustfile} -O -o {output}"], shell=True)
        if clean:
            os.remove(rustfile)

        if not pathlib.Path(output).exists():
            con.log(f"\"{file}\": uses unsupported features and did not generate a valid rust file")
            return 1

        if execute:
            subprocess.run(str(pathlib.Path(output).absolute()))

    return 0

if __name__ == "__main__":
    args = generate_arguments()

    sys.exit(
        transpile(**vars(args))
    )
        return function(tree)

def generate_arguments() -> argparse.Namespace:
    argument_parser = argparse.ArgumentParser(usage=f"python {SCRIPT_NAME} <options> <file>",
                                              description="Python-To-Rust transpiler and compiler")

    argument_parser.add_argument("file", type=str, help="input python file")
    argument_parser.add_argument("-r", "--rout", "--output-rust", required=False, type=str, help="output Rust file")
    argument_parser.add_argument("-o", "--output", "--output-exe", required=False, type=str, help="output executable file")
    argument_parser.add_argument("-C", "--compile", action="store_true", default=False, help="generate an executable file")
    argument_parser.add_argument("-E", "--execute", action="store_true", default=False,
                                 help="execute the produced executable if any")
    argument_parser.add_argument("-c", "--clean", action="store_true", default=False, help="delete intermediate files")
    argument_parser.add_argument("-S", "--style",  action="store_true", default=False, help="automatically style/format produced rust files")

    args = argument_parser.parse_args()

    return args

def real_transpile(tree: ast.Module) -> str:
    return RustTranspiler.transpile(tree)

def transpile(file: str, rout: str | None = None, output: str | None = None, compile: bool = True, clean: bool = True,
              execute: bool = False, style: bool = False) -> int:
    filepath = pathlib.Path(file)

    if not filepath.exists():
        con.log(f"\"{file}\": does not exist")
        return 1
    elif not filepath.is_file():
        con.log(f"\"{file}\": is not a file")

    try:
        content = filepath.read_text(encoding="utf-8")
    except PermissionError:
        con.log(f"\"{file}\": not enough permission to access")
        return 1
    except UnicodeDecodeError:
        con.log(f"\"{file}\": encoding error (utf-8)")
        return 1
    except OSError as e:
        con.log(f"\"{file}\": not accessible; {" ".join(e.args)}")
        return 1

    try:
        parsed = ast.parse(content, str(filepath.relative_to(".")), "exec", type_comments=True, optimize=2)
    except SyntaxError as e:
        con.log(f"\"{file}\": syntax error at line {e.lineno}, run with Python to get more information")
        return 1

    transpiled = real_transpile(parsed)
    *parts, _ = filepath.name.split(".")
    filepath_no_ext = ".".join(parts)
    rustfile = rout or pathlib.Path(f"/tmp/rustpy_{filepath_no_ext}.rs")  # do windows stuff here eventually
    output = output or f"{filepath_no_ext}{EXE_EXTENSION}"

    with open(rustfile, "w") as f:
        f.write(transpiled)

    if style:
        subprocess.run([f"rustfmt {rustfile}"], shell=True)

    if compile:
        try: os.remove(output)
        except FileNotFoundError: pass

        subprocess.run([f"rustc {rustfile} -O -o {output}"], shell=True)
        if clean:
            os.remove(rustfile)

        if not pathlib.Path(output).exists():
            con.log(f"\"{file}\": uses unsupported features and did not generate a valid rust file")
            return 1

        if execute:
            subprocess.run(str(pathlib.Path(output).absolute()))

    return 0

if __name__ == "__main__":
    args = generate_arguments()

    sys.exit(
        transpile(**vars(args))
    )
