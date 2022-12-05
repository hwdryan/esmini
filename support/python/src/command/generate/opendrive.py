from jinja2 import Environment, FileSystemLoader, select_autoescape
import xml.etree.ElementTree as ET
import json
import os
from support.python.src.globals import ESMINI_DIRECTORY_SUPPORT, ESMINI_DIRECTORY_ROOT


class OpenDrive:
    def generate_file(self, data, output):
        outputfolder = os.path.join(ESMINI_DIRECTORY_SUPPORT, "generated")
        if not os.path.exists(outputfolder):
            os.mkdir(outputfolder)
        output_file = os.path.join(outputfolder, output + ".hpp")

        # Dump dict to json for testing/fault tracing
        self.print_dict(output_file, data)

        # Generate the hpp file
        self.create_hpp_files(output_file, data)

    def create_hpp_files(self, output_file, data):
        template_folder = os.path.join(ESMINI_DIRECTORY_SUPPORT, "jinja")
        template_file = "hpp_template.j2"
        env = Environment(
            autoescape=select_autoescape(),
            loader=FileSystemLoader(template_folder),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        template = env.get_template(template_file)
        content = template.render(data)
        with open(output_file, mode="w", encoding="utf-8") as message:
            message.write(content)

    def print_dict(self, output_file, data):
        with open(output_file + ".json", mode="w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)
            file.close()

    def parser(self, file, name):
        parsed_data = {}
        tree = ET.parse(file)
        root = tree.getroot()
        self.parse_children(root, parsed_data)
        return {"name": name, "data": parsed_data}

    def parse_children(self, parent, data):
        attributes_dict = {}
        for child in parent:
            if "complexType" in child.tag or "simpleType" in child.tag:
                child_sub_dict = self.parse_children(child, {})
                name = child.attrib["name"]
                if name.startswith("t_"):
                    name = "class " + name
                elif name.startswith("e_"):
                    name = "enum class " + name
                data.update({name: child_sub_dict})

            elif "extension" in child.tag or "restriction" in child.tag:
                base = child.attrib["base"]
                if base == "xs:string":
                    base = "string"
                elif base == "xs:double":
                    base = "double"
                data.update({"base": {base: self.parse_children(child, {})}})

            elif "sequence" in child.tag:
                data.update({"sequence": self.parse_children(child, {})})

            elif "enumeration" in child.tag:
                value = child.attrib["value"]
                value = self.fix_non_legal_chars(value)
                data.update({value: ""})

            elif "element" in child.tag:
                attributes = child.attrib
                if len(attributes) > 1:
                    attributes["type"] = self.replace_cpp_types(attributes["type"])
                data.update({child.attrib["name"]: attributes})

            elif "attribute" in child.tag:
                attributes = child.attrib
                if len(attributes) > 1:
                    attributes["type"] = self.replace_cpp_types(attributes["type"])
                attributes_dict.update({child.attrib["name"]: attributes})

            else:
                self.parse_children(child, data)
        if len(attributes_dict) != 0:
            data.update({"attributes": attributes_dict})
        return data

    def replace_cpp_types(self, attribute):
        if attribute == "xs:string":
            attribute = "std::string"
        elif attribute == "xs:double":
            attribute = "double"
        elif attribute == "xs:integer":
            attribute = "int"
        elif attribute == "xs:float":
            attribute = "float"
        elif attribute == "t_grEqZero":
            attribute = "double"
        elif attribute == "t_grZero":
            attribute = "double"
        return attribute

    def fix_non_legal_chars(self, string):
        string = string.replace("/", "")
        string = string.replace(" ", "_")
        return string

    def generate_opendrive(self):
        opendrive_schema_path = os.path.join(
            ESMINI_DIRECTORY_ROOT, "..", "OpenDrive1_7_0"
        )
        files_to_generate = [
            (os.path.join(opendrive_schema_path, "opendrive_17_core.xsd"), "Core"),
            (os.path.join(opendrive_schema_path, "opendrive_17_road.xsd"), "Road"),
            (os.path.join(opendrive_schema_path, "opendrive_17_lane.xsd"), "Lane"),
            (
                os.path.join(opendrive_schema_path, "opendrive_17_junction.xsd"),
                "Junction",
            ),
            (os.path.join(opendrive_schema_path, "opendrive_17_object.xsd"), "Object"),
            (os.path.join(opendrive_schema_path, "opendrive_17_signal.xsd"), "Signal"),
            (
                os.path.join(opendrive_schema_path, "opendrive_17_railroad.xsd"),
                "Railroad",
            ),
        ]
        for opendrive, output in files_to_generate:
            print("Parsing: ", output)
            with open(opendrive, mode="r", encoding="utf-8") as input:
                data = self.parser(input, output)
            self.generate_file(data, output)
            print(f"Generated: {output}")