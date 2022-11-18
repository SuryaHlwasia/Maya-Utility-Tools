from maya import cmds

suffixes = {
    "mesh":"geo",
    "joint":"jnt",
    "camera": None,
    "ambientLight":"lgt"
}

d_suffix = "grp"
def rename(selection=False):
    """
    This function will rename any objects to have the correct suffix
    Args:
        selection: Whether or not we use the current selection

    Returns:
        A list of all the selected objects we operated on

    """
    objects = (cmds.ls(selection=selection,dag=True,long=True))

    if(selection and not objects):
        raise RuntimeError("You don't have anything selected.")

    if(len(objects) == 0):
        objects = cmds.ls(dag = True, long = True)
    objects.sort(key=len, reverse = True)

    for obj in objects:
        shortName = obj.split("|")[-1]
        children = cmds.listRelatives(obj,children=True,fullPath=True) or []
        if(len(children)==1):
            child = children[0]
            objType = cmds.objectType(child)
        else:
            objType = cmds.objectType(obj)

        suffix = suffixes.get(objType, d_suffix)

        if (suffix is None):
            continue
        if(obj.endswith('_'+suffix)):
            continue

        newName = "{}_{}".format(shortName, suffix)
        cmds.rename(obj,newName)
        index = objects.index(obj)

        objects[index] = newName
    return(objects)