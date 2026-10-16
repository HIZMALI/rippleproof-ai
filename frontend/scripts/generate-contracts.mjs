/** Generate runtime validators and TS types from the real FastAPI schema.
 * Default is the localhost OpenAPI, never a fixture or imagined interface.
 */
import { writeFile } from "node:fs/promises";

const response = await fetch(
  process.env.OPENAPI_URL ?? "http://127.0.0.1:18000/openapi.json",
);
if (!response.ok) throw new Error(`OpenAPI unavailable (${response.status})`);
const api = await response.json();
const models = api.components.schemas;
const generated = new Map();
const visiting = new Set();

function schema(s) {
  if (s.$ref) {
    const name = s.$ref.split("/").at(-1);
    generate(name);
    return `${name}Schema`;
  }
  if (s.const !== undefined) return `z.literal(${JSON.stringify(s.const)})`;
  if (s.enum) return `z.enum(${JSON.stringify(s.enum)})`;
  if (s.anyOf) return `z.union([${s.anyOf.map(schema).join(", ")}])`;
  if (s.type === "null") return "z.null()";
  if (s.type === "array") return `z.array(${schema(s.items)})`;
  if (s.type === "object" || s.properties) {
    if (!s.properties)
      return `z.record(z.string(), ${s.additionalProperties && s.additionalProperties !== true ? schema(s.additionalProperties) : "z.json()"})`;
    const required = new Set(s.required ?? []);
    const props = Object.entries(s.properties).map(([key, value]) => {
      let valueSchema = schema(value);
      if (!required.has(key)) {
        valueSchema +=
          value.default !== undefined
            ? `.default(${JSON.stringify(value.default)})`
            : ".optional()";
      }
      return `${JSON.stringify(key)}: ${valueSchema}`;
    });
    return `z.object({${props.join(",\n")}})${s.additionalProperties === false ? ".strict()" : ""}`;
  }
  if (s.type === "boolean") return "z.boolean()";
  if (s.type === "integer" || s.type === "number") {
    let value = "z.number()" + (s.type === "integer" ? ".int()" : "");
    if (s.minimum !== undefined) value += `.min(${s.minimum})`;
    if (s.exclusiveMinimum !== undefined) value += `.gt(${s.exclusiveMinimum})`;
    return value;
  }
  if (s.type === "string") {
    let value = s.format === "date" ? "z.iso.date()" : "z.string()";
    if (s.minLength) value += `.min(${s.minLength})`;
    if (s.maxLength) value += `.max(${s.maxLength})`;
    if (s.pattern) value += `.regex(new RegExp(${JSON.stringify(s.pattern)}))`;
    return value;
  }
  return "z.json()";
}
function generate(name) {
  if (generated.has(name)) return;
  if (visiting.has(name))
    throw new Error(`Unexpected recursive schema ${name}`);
  visiting.add(name);
  const definition = name === "JsonValue" ? "z.json()" : schema(models[name]);
  generated.set(
    name,
    `export const ${name}Schema = ${definition};\nexport type ${name} = z.infer<typeof ${name}Schema>;`,
  );
  visiting.delete(name);
}
Object.keys(models).sort().forEach(generate);
await writeFile(
  new URL("../src/api/contracts.ts", import.meta.url),
  '// Generated from live FastAPI OpenAPI. Run npm run contracts; do not hand-edit.\nimport { z } from "zod";\n\n' +
    [...generated.values()].join("\n\n") +
    "\n",
);
console.log(
  `Generated ${generated.size} runtime validators from FastAPI ${api.info.version}.`,
);
