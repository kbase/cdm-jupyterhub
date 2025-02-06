import { globSync } from "glob";

const srcFolderPath = globSync("./src")[0];

const entriesFromGlob = (glob) => {
  console.log(srcFolderPath);
  return Object.fromEntries(
  globSync(srcFolderPath + "/" + glob).map((path) => {
    const entryName = path.split(srcFolderPath + "/")[1].split(".ts")[0];
    return [entryName, path];
  })
);}

export default {
  input: {
    ...entriesFromGlob("templates/**/*.ts")
  },
  output: {
    dir: "./ts-build",
    format: "cjs",
  },
};
