# CJ2IFC
Converter for CityJSON files to IFC.

-- WARNING --

CJ2IFC only came into being 14/04/2021. Be prepared for lots of bugs, unfinished implementations and little to no documentation!

## Dependencies
- [IfcOpenShell](https://github.com/IfcOpenShell/IfcOpenShell)
- [CJIO](https://github.com/cityjson/cjio)

## Usage of CJ2IFC
Following command will execute a conversion from CityJSON to IFC
  
    CJ2IFC.py [-i input file] [-o output file] [-n identification attribute]

## Implemented geometries
- [ ] "MultiPoint"
- [ ] "MultiLineString"
- [ ] "MultiSurface"
- [ ] "CompositeSurface"
- [ ] "Solid"
- [ ] "MultiSolid"
- [x] "CompositeSolid": exterior shell
- [ ] "CompositeSolid": interior shell
- [ ] "GeometryInstance" 

## TODO
- [ ] CityJSON Attributes as IFC properties in 'CityJSON' pset
- [ ] Implement georeferencing
- [ ] Do not use template IFC for new IFC file, but make IFC file from scratch
