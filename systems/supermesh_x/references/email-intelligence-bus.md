# Email Intelligence Bus

Gmail is an authorized-private ingestion lane, not a public search provider. Normalize message/thread/attachment metadata into private evidence records and classify useful market/research types such as newsletters, TradingView or market alerts, broker notices, research notes, GitHub notifications, and company/investor-relations mail.

Raw message bodies, private attachments, recipient data, and account identifiers stay inside the private lane. Public-provider queries may use only explicitly allowlisted derived features such as ticker, topic, timestamp bucket, or non-sensitive sentiment/category labels. Sending, forwarding, deleting, archiving, labeling, or modifying drafts requires the runtime's normal write authority and explicit user intent.

For Substack, prefer public RSS/public pages for public evidence; use an authorized inbox copy as private evidence when the user legitimately receives it. Deduplicate the inbox copy against public copies without converting private content into public-provider payloads.
