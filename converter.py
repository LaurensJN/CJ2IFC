import ifcopenshell
import warnings

JSON_TO_IFC = {
    "Building": ["IfcBuilding"],
    "BuildingPart": ["IfcBuilding", {"CompositionType": "Partial"}],  # CompositionType: Partial
    "BuildingInstallation": ["IfcDistributionElement"],
    "Road": ["IfcCivilElement"],
    "TransportSquare": ["IfcSpace"],
    "TINRelief": ["IfcGeographicElement"],
    "WaterBody": ["IfcGeographicElement"],
    "LandUse": ["IfcGeographicElement"],
    "PlantCover": ["IfcGeographicElement"],
    "SolitaryVegetationObject": ["IfcGeographicElement"],
    "CityFurniture": ["IfcFurnishingElement"],
    "GenericCityObject": ["IfcCivilElement"],
    "Bridge": ["IfcCivilElement"],
    "BridgePart": ["IfcCivilElement"],
    "BridgeInstallation": ["IfcCivilElement"],
    "BridgeConstructionElement": ["IfcCivilElement"],
    "Tunnel": ["IfcCivilElement"],
    "TunnelPart": ["IfcCivilElement"],
    "TunnelInstallation": ["IfcCivilElement"],
    "CityObjectGroup": ["IfcCivilElement"],
}

class Converter:
    def __init__(self):
        self.city_model = None
        self.IFC_model = None
        self.properties = {}
        self.configuration()

    def configuration(self, file_destination="output.ifc", name_attribute=None):
        self.properties["file_destination"] = file_destination
        self.properties["name_attribute"] = name_attribute


    def convert(self, city_model):
        self.city_model = city_model
        self.create_new_file()
        self.create_metadata()
        self.build_vertices()
        self.create_IFC_classes()
        self.write_file()

    def create_metadata(self):
        # Georeferencing
        if self.city_model.is_transform():
            self.properties["local_scale"] = self.city_model.j['transform']['scale']
            self.properties["local_translation"] = self.city_model.j['transform']['translate']

        self.properties["owner_history"] = self.IFC_model.by_type("IfcOwnerHistory")[0]

    def create_new_file(self):
        self.IFC_model = ifcopenshell.open('example/template.ifc')
        self.IFC_site = self.IFC_model.by_type('IfcSite')[0]
        self.IFC_representation_context = self.IFC_model.by_id(21)
        # self.IFC_model = ifcopenshell.file(schema='IFC4')

    def write_file(self):
        self.IFC_model.write(self.properties["file_destination"])

    def build_vertices(self):
        vertices = self.city_model.j["vertices"]
        self.vertex_dict = {}
        for vertex in vertices:
            if "local_scale" in self.properties:
                IFC_vertex = tuple([float(coord) * coord_scale
                                    for coord, coord_scale
                                    in zip(vertex, self.properties["local_scale"])])
            else:
                IFC_vertex = [float(coord) for coord in vertex]

            IFC_cartesian_point = self.IFC_model.create_entity("IfcCartesianPoint", IFC_vertex)
            self.vertex_dict[tuple(vertex)] = IFC_cartesian_point

    def create_IFC_classes(self):
        for obj_id, obj in self.city_model.get_cityobjects().items():

            # CityJSON type to class
            mapping = JSON_TO_IFC[obj.type]
            IFC_class = mapping[0]
            data = {}
            # Add attributes if it is specified in mapping
            # Example: BuildingPart to IfcBuilding with CompositionType: Partial
            if len(mapping) > 1:
                data = mapping[1]

            # attributes
            IFC_name = None
            if "name_attribute" in self.properties and self.properties["name_attribute"] in obj.attributes:
                IFC_name = obj.attributes[self.properties["name_attribute"]]

            # TODO children

            # TODO parents

            # TODO geometry_type

            # geometry_lod
            lod = 0
            geometry = None
            for geom in obj.geometry:
                if geom.lod > lod:
                    geometry = geom
                    lod = geom.lod
            IFC_geometry = self.create_IFC_geometry(geometry)

            data["GlobalId"] = ifcopenshell.guid.new()
            data["Name"] = IFC_name
            if IFC_geometry:
                # semantic_surfaces (RoofSurface/GroundSurface/WallSurface)
                shape_representation = self.IFC_model.create_entity("IfcShapeRepresentation",
                                                                    self.IFC_representation_context, 'Body', 'Brep',
                                                                    [IFC_geometry])
                product_representation = self.IFC_model.create_entity("IfcProductDefinitionShape",
                                                                      Representations=[shape_representation])
                data["Representation"] = product_representation


            IFC_object = self.IFC_model.create_entity(IFC_class, **data)
            # Define aggregation
            self.IFC_model.create_entity("IfcRelAggregates",
                                         **{"GlobalId": ifcopenshell.guid.new(),
                                            "RelatedObjects": [IFC_object],
                                            "RelatingObject": self.IFC_site}
                                         )
            self.create_property_set(obj.attributes, IFC_object)

    def create_IFC_geometry(self, geometry):
        if geometry.type != "Solid":
            warnings.warn("Types other than solids are not yet supported")
            return

        outershell = geometry.boundaries[0]
        faces = []
        for surface in outershell:  # exterior shell
            for face in surface:
                vertices = []
                for vertex in face:
                    vertices.append(self.vertex_dict[tuple(vertex)])
                polyloop = self.IFC_model.create_entity("IfcPolyLoop", vertices)
                outerbound = self.IFC_model.create_entity("IfcFaceOuterBound", polyloop, True)
                faces.append(self.IFC_model.create_entity("IfcFace", [outerbound]))

        if len(geometry.boundaries) == 1:
            shell = self.IFC_model.create_entity("IfcClosedShell", faces)
            IFC_geometry = self.IFC_model.create_entity("IfcFacetedBrep", shell)
            return IFC_geometry

        # TODO: INTERIOR SHELL
        warnings.warn("Solid interior shell not yet supported")
        return
        # for boundary in geometry.boundaries[1]:  # interior shell
        #     for face in boundary:
        #         for triangle in face:
        #             print(triangle)
        # print(geometry.boundaries)

    def create_property_set(self, CJ_attributes, IFC_entity):

        IFC_object_properties = []
        for property, val in CJ_attributes.items():
            if val == None:
                continue

            if type(val) == int:
                IFC_type = "IfcInteger"
            elif type(val) == float:
                IFC_type = "IfcReal"
            elif type(val) == bool:
                IFC_type = "IfcBoolean"
            else:
                IFC_type = "IfcText"

            IFC_object_properties.append(
                self.IFC_model.createIfcPropertySingleValue(property, property,
                                                            self.IFC_model.create_entity(IFC_type, val), None)
            )
        property_set = self.IFC_model.createIfcPropertySet(ifcopenshell.guid.new(),
                                                           self.properties["owner_history"],
                                                           "CityJSON_attributes",
                                                           None,
                                                           IFC_object_properties)

        self.IFC_model.createIfcRelDefinesByProperties(ifcopenshell.guid.new(),
                                                       self.properties["owner_history"],
                                                       None, None, [IFC_entity],
                                                       property_set)
