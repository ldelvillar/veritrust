---
status: accepted
---

# An Analysis is true only when every Claim is true

ADR-0002 stopped a true Claim from offsetting a false one, but it still called an Analysis true when some Claims were true and the rest uncertain. The forwarded message that prompted it, «Beber lejía diluida mata el virus en el organismo. Una sobredosis de paracetamol causa daño hepático», came out true again (Confidence 0.78): no Source was judged relevant to the bleach Claim, so it was uncertain and the paracetamol Claim decided alone. Now an Analysis is true only when every Claim is true. True Claims next to uncertain ones make it uncertain, with the mean Confidence of the uncertain Claims and no Credibility. False and Partly false are unchanged, and an uncertain Claim never softens a false one. This amends ADR-0002's rule for true.

A Claim is uncertain whenever it could not be verified, not only when the literature is silent or split: also when the cap of 8 searched Claims leaves it out, when it has no usable query, or when its Sources or the judge fail. So a text with more than 8 Claims, or one whose search partly failed, can no longer come out true. That is intended: a true Verdict covers everything the text asserts. Replaying the recorded Stances of the 13–14 October runs, the bleach and homeopathy texts (expected false) move from true to uncertain, one correct true text («La quimioterapia provoca efectos adversos como náuseas y caída del cabello») moves to uncertain, and no single-Claim text changes.

## Considered Options

- **Keep "true if some are true and none are false"**: rejected. A hoax next to a true fact gets a true Verdict whenever the literature ignores the hoax, which is common for folk remedies.
- **Leave out only the Claims the search never reached** (cap, outage): rejected. A hoax placed ninth in a text would pass the same way, and Evidence coverage already reports the gap.
- **A new Verdict such as "partly verified"**: rejected for now. It adds a value to the Verdict vocabulary, the database, the API and the frontend for a case that uncertain already describes.
