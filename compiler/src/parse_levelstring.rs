use crate::builtins::{Block, Group, Id, Item};
use crate::gd_props::{kind_of, Kind};
use crate::{builtins::Color, leveldata::ObjParam, value::Value};
use errors::RuntimeError;
use parser::ast::ObjectMode;

fn id16(val: &str) -> Option<u16> {
    val.trim().parse::<u16>().ok()
}

/// Reads one property value according to what the property holds for this object.
/// Anything that doesn't look like what it should be is kept as text instead of failing,
/// so levels containing unknown or malformed properties can still be loaded.
fn parse_value(kind: Kind, val: &str) -> ObjParam {
    let fallback = || ObjParam::Text(val.to_string());
    match kind {
        Kind::Bool => ObjParam::Bool(val.trim() == "1"),
        Kind::Text => ObjParam::Text(val.to_string()),
        Kind::Group => id16(val).map_or_else(fallback, |id| {
            ObjParam::Group(Group {
                id: Id::Specific(id),
            })
        }),
        Kind::Color => id16(val).map_or_else(fallback, |id| {
            ObjParam::Color(Color {
                id: Id::Specific(id),
            })
        }),
        Kind::Block => id16(val).map_or_else(fallback, |id| {
            ObjParam::Block(Block {
                id: Id::Specific(id),
            })
        }),
        Kind::Item => id16(val).map_or_else(fallback, |id| {
            ObjParam::Item(Item {
                id: Id::Specific(id),
            })
        }),
        Kind::GroupList => {
            let groups: Option<Vec<Group>> = val
                .split('.')
                .map(|g| {
                    id16(g).map(|id| Group {
                        id: Id::Specific(id),
                    })
                })
                .collect();
            groups.map_or_else(fallback, ObjParam::GroupList)
        }
        Kind::GroupPairs => {
            let parts: Vec<&str> = val.split('.').collect();
            if parts.len() % 2 != 0 {
                return fallback();
            }
            let pairs: Option<Vec<(Group, f64)>> = parts
                .chunks(2)
                .map(|c| {
                    let g = id16(c[0])?;
                    let n = c[1].trim().parse::<f64>().ok()?;
                    Some((
                        Group {
                            id: Id::Specific(g),
                        },
                        n,
                    ))
                })
                .collect();
            pairs.map_or_else(fallback, ObjParam::GroupPairs)
        }
        Kind::Number => val
            .trim()
            .parse::<f64>()
            .map_or_else(|_| fallback(), ObjParam::Number),
    }
}

pub fn parse_levelstring(ls: &str) -> Result<Vec<Value>, RuntimeError> {
    let mut obj_strings = ls.split(';');
    obj_strings.next(); // skip the header
    let mut objs = Vec::new();
    for obj_string in obj_strings {
        if obj_string.is_empty() {
            continue;
        }
        let parts = obj_string.split(',').collect::<Vec<&str>>();
        let pairs: Vec<(&str, &str)> = parts.chunks_exact(2).map(|c| (c[0], c[1])).collect();

        let obj_id = pairs
            .iter()
            .find(|(k, _)| *k == "1")
            .and_then(|(_, v)| id16(v))
            .unwrap_or(0);
        // the pulse trigger's target is a group when its group mode (52) is set, a color otherwise
        let pulse_group_mode = pairs.iter().any(|(k, v)| *k == "52" && *v == "1");

        let mut obj = Vec::new();
        for (key, val) in pairs {
            let key = match key.parse::<u16>() {
                Ok(k) => k,
                Err(_) => continue,
            };

            let prop = if key == 1 {
                ObjParam::Number(obj_id as f64)
            } else if obj_id == 1006 && key == 51 {
                parse_value(
                    if pulse_group_mode {
                        Kind::Group
                    } else {
                        Kind::Color
                    },
                    val,
                )
            } else if obj_id == 899 && key == 51 {
                // legacy colour trigger target
                parse_value(Kind::Color, val)
            } else if obj_id == 1615 && key == 80 {
                // counter display: the item id is a plain number there
                parse_value(Kind::Item, val)
            } else {
                parse_value(kind_of(obj_id, key), val)
            };
            obj.push((key, prop));
        }
        objs.push(Value::Obj(obj, ObjectMode::Object));
    }
    Ok(objs)
}
