import { Composition } from "remotion";
import { PromptForgeDemo, TOTAL } from "./Video";

export const Root = () => (
  <Composition id="PromptForgeDemo" component={PromptForgeDemo} durationInFrames={TOTAL} fps={30} width={1920} height={1080} />
);
