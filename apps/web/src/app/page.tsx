import { redirect } from "next/navigation";

/**
 * The product IS the killshot. Opening on a generic landing would violate the
 * positioning rule (RECON-B: never open on "watch me capture my screen").
 * Route straight to the forensic compare page for the demo task.
 */
export default function Home() {
  redirect("/runs/demo_login_flow/compare");
}
