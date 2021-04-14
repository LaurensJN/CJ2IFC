import ifcopenshell
from ifcopenshell import geom

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
        self.configuration()

    def configuration(self, file_destination="example/example_output.ifc", name_attribute=None):
        self.file_destination = file_destination
        self.name_attribute = name_attribute

    def convert(self, city_model):
        self.city_model = city_model
        self.create_new_file()
        self.local_scale = self.city_model.j['transform']['scale']
        self.local_translation = self.city_model.j['transform']['translate']
        self.build_vertices()
        self.create_IFC_classes()

        self.write_file()

    def create_new_file(self):
        self.IFC_model = ifcopenshell.open('example/template.ifc')
        self.IFC_site = self.IFC_model.by_type('IfcSite')[0]
        self.IFC_representation_context = self.IFC_model.by_id(21)
        # self.IFC_model = ifcopenshell.file(schema='IFC4')

    def write_file(self):
        self.IFC_model.write(self.file_destination)

    def build_vertices(self):
        vertices = self.city_model.j["vertices"]
        self.vertex_dict = {}
        for vertex in vertices:
            IFC_vertex = tuple([float(coord) * coord_scale
                                for coord, coord_scale
                                in zip(vertex, self.local_scale)])
            IFC_cartesian_point = self.IFC_model.create_entity("IfcCartesianPoint", IFC_vertex)
            self.vertex_dict[tuple(vertex)] = IFC_cartesian_point

        pass

    def create_IFC_classes(self):
        for obj_id, obj in self.city_model.get_cityobjects().items():
            # type
            mapping = JSON_TO_IFC[obj.type]
            IFC_class = mapping[0]
            data = {}
            if len(mapping) > 1:
                data = mapping[1]

            # attributes
            IFC_name = None
            if self.name_attribute and self.name_attribute in obj.attributes:
                IFC_name = obj.attributes[self.name_attribute]

            ## name: attributes.identificatie

            # children

            # parents

            # geometry_type

            # geometry_lod
            lod = 0
            geometry = None
            for geom in obj.geometry:
                if geom.lod > lod:
                    geometry = geom
                    lod = geom.lod
            IFC_geometry = self.create_IFC_geometry(geometry)

            # IFCSHAPEREPRESENTATION(  # 21,'Body','Brep',(#13328));

            # semantic_surfaces (RoofSurface/GroundSurface/WallSurface)
            shape_representation = self.IFC_model.create_entity("IfcShapeRepresentation",
                                                                self.IFC_representation_context, 'Body', 'Brep',
                                                                [IFC_geometry])
            product_representation = self.IFC_model.create_entity("IfcProductDefinitionShape",
                                                                  Representations=[shape_representation])

            data["GlobalId"] = ifcopenshell.guid.new()
            data["Name"] = IFC_name
            data["Representation"] = product_representation
            IFC_object = self.IFC_model.create_entity(IFC_class, **data)

            # Define aggregation
            self.IFC_model.create_entity("IfcRelAggregates",
                                         **{"GlobalId": ifcopenshell.guid.new(),
                                            "RelatedObjects": [IFC_object],
                                            "RelatingObject": self.IFC_site}
                                         )

    def create_IFC_geometry(self, geometry):
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
        for boundary in geometry.boundaries[1]:  # interior shell
            for face in boundary:
                for triangle in face:
                    print(triangle)
        # print(geometry.boundaries)