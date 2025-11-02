# StArranja Database Architecture (MongoDB)

## 1. Introduction

This document outlines the MongoDB data model for the StArranja project. The architecture is designed to be scalable, performant, and flexible, supporting all functional and non-functional requirements for the workshop management system.

The model is **hybrid**, using a combination of **Referencing** (for data consistency) and **Embedding** (for query performance) to create a robust system.

### Key Technical Standards
* **Dates:** All date fields must be stored using the `ISODate` type for universal, sortable timekeeping.
* **Finance:** All monetary values (prices, totals) and non-integer quantities (like hours) **must** use the `Decimal128` type to prevent floating-point rounding errors.
* **Relations:**
    * `ObjectId` is used for internal references (e.g., `clientId`, `vehicleId`).
    * `String` (UUID) is used for external references to the PostgreSQL `users` table (e.g., `mechanicsIds`).

---

## 2. Visual Schema Diagram

![StArranja Database (MongoDB) Schema](./images/mongodb-desing-v3.png)

---

## 3. Collection: `clients`

Stores the primary customer records for the workshop. This collection is referenced by `vehicles`, `workOrders`, and `invoices`.

### Schema Definition

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `_id` | `ObjectId` | ✓ | Unique document identifier. |
| `name` | `String` | ✓ | Customer's full name. |
| `nif` | `String` | ✓ | Customer's 9-digit NIF (Tax ID). Must be unique. |
| `phone` | `String` | ✓ | Primary contact phone number. |
| `email` | `String` | | Customer's email address. |
| `address` | `Object` | | Embedded object for the customer's address. |
| `address.street`| `String` | | |
| `address.city` | `String` | | |
| `address.zipCode`| `String` | | |
| `createdAt` | `ISODate` | ✓ | Timestamp when the client was created. |
| `updatedAt` | `ISODate` | ✓ | Timestamp of the last update. |

### Indexes

| Field(s) | Type | Purpose |
| :--- | :--- | :--- |
| `{ nif: 1 }` | **Unique** | Enforces that no two clients can have the same NIF. |
| `{ phone: 1 }` | Simple | Fast lookup by phone number. |
| `{ email: 1 }` | Unique, Partial | Enforces unique emails *if* the email field exists. |

---

## 4. Collection: `vehicles`

Stores all vehicle records. Each vehicle is owned by a single client from the `clients` collection.

### Schema Definition

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `_id` | `ObjectId` | ✓ | Unique document identifier. |
| `clientId` | `ObjectId` | ✓ | **Reference** to the `_id` in the `clients` collection. |
| `licensePlate` | `String` | ✓ | Vehicle's license plate. Must be unique. |
| `brand` | `String` | ✓ | e.g., "Renault" |
| `model` | `String` | ✓ | e.g., "Clio" |
| `vin` | `String` | | 17-character Vehicle Identification Number (Chassis Nr.). |
| `lastKnownKilometers` | `Number` | | Last recorded mileage (optional). |
| `createdAt` | `ISODate` | ✓ | Timestamp when the vehicle was created. |
| `updatedAt` | `ISODate` | ✓ | Timestamp of the last update. |

### Indexes

| Field(s) | Type | Purpose |
| :--- | :--- | :--- |
| `{ licensePlate: 1 }` | **Unique** | Enforces that no two vehicles can have the same license plate. |
| `{ clientId: 1 }` | Simple | Fast lookup for all vehicles belonging to a specific client. |
| `{ vin: 1 }` | Unique, Partial | Enforces unique VINs *if* the VIN field exists. |

---

## 5. Collection: `workOrders`

This is the core collection, tracking the entire lifecycle of a repair job. It references a `client` and `vehicle` and embeds its own `quote` and `items`.

### Schema Definition

| Field                   | Type                | Required | Description                                                                                                                                                                                       |
|:------------------------|:--------------------|:---------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `_id`                   | `ObjectId`          | ✓        | Unique document identifier.                                                                                                                                                                       |
| `workOrderNumber`       | `String`            | ✓        | Sequential, human-readable ID (e.g., "2025-0001").                                                                                                                                                |
| `clientId`              | `ObjectId`          | ✓        | **Reference** to the `_id` in the `clients` collection.                                                                                                                                           |
| `vehicleId`             | `ObjectId`          | ✓        | **Reference** to the `_id` in the `vehicles` collection.                                                                                                                                          |
| `mechanicsIds`          | `Array`             |          | Array of `String` (UUIDs) **referencing** the `users` table in PostgreSQL.                                                                                                                        |
| `status`                | `String`            | ✓        | The current stage of the job. Must be one of: `AwaitingDiagnostic`, `AwaitingApproval`, `Approved`, `AwaitingParts`, `InProgress`, `Completed`, `Invoiced`, `Delivered`, `Declined`, `Cancelled`. |
| `isActive`              | `Boolean`           | ✓        | Controls RB02. `true` if WO is not in a final state (e.g. 'Completed', 'Invoiced'). Must be managed by the application.                                                                           |
| `quote`                 | `Object`            |          | **Embedded** object for the diagnostic and budget.                                                                                                                                                |
| `items`                 | `Array`             |          | **Embedded** array of objects (see `items` schema below).                                                                                                                                         |
| `finalTotalWithoutIVA`  | `Decimal128`        |          | Final total calculated from the `items` array.                                                                                                                                                    |
| `finalTotalIVA`         | `Decimal128`        |          | Final total calculated from the `items` array.                                                                                                                                                    |
| `finalTotalWithIVA`     | `Decimal128`        |          | Final total calculated from the `items` array.                                                                                                                                                    |
| `entryDate`             | `ISODate`           | ✓        | Timestamp: Vehicle check-in.                                                                                                                                                                      |
| `diagnosisRegisteredAt` | `ISODate`           |          | Timestamp: Quote/diagnostic registered.                                                                                                                                                           |
| `quoteApprovedAt`       | `ISODate`           |          | Timestamp: Customer approval (RB06).                                                                                                                                                              |
| `completedAt`           | `ISODate`           |          | Timestamp: Work completed (triggers RB07).                                                                                                                                                        |
| `deliveredAt`           | `ISODate`           |          | Timestamp: Vehicle delivered to customer.                                                                                                                                                         |
| `createdAt`             | `ISODate`           | ✓        | Timestamp when the document was created.                                                                                                                                                          |
| `updatedAt`             | `ISODate`           | ✓        | Timestamp of the last update.                                                                                                                                                                     |
| **`createdById`**       | **`String (UUID)`** | ✓        | **Reference to the user (PostgreSQL) who created the WO.**                                                                                                                                        |

### Embedded Schema: `quote`

| Field | Type | Description |
| :--- | :--- | :--- |
| `clientObservations` | `String` | The customer's complaint/notes. |
| `diagnostic` | `String` | The mechanic's technical diagnosis (RF04). |
| `isApproved` | `Boolean` | `true` when the customer approves the budget (RB06). |

### Embedded Schema: `items` (Array element)

| Field | Type | Description |
| :--- | :--- | :--- |
| `type` | `String` | Enum: `Part` or `Labor`. |
| `description` | `String` | e.g., "5W-30 oil" or "Filter change labor". |
| `reference` | `String` | Part number or internal code (RB03). |
| `quantity` | `Decimal128` | Units or hours (RB03). |
| `unitPriceWithoutIVA`| `Decimal128`| Cost per unit/hour (RB03, RF06). |
| `ivaRate` | `Decimal128`| Tax rate, e.g., `0.23`. |
| `totalPriceWithIVA` | `Decimal128`| Calculated total for the line item (RF06). |

### Indexes

| Field(s) | Type | Purpose |
| :--- | :--- | :--- |
| `{ vehicleId: 1 }` | **Partial, Unique** | **Implements RB02**. `{"isActive": true}` <br> Ensures a vehicle has only ONE active work order. (FerretDB/DocumentDB compatible). |
| `{ workOrderNumber: 1 }`| **Unique** | Fast lookup by the human-readable number. |
| `{ status: 1 }` | Simple | Optimizes simple queries by status (e.g., "all `InProgress` WOs"). |
| `{ entryDate: -1 }` | Simple | Accelerates sorting by entry date (RF10). |
| `{ status: 1, entryDate: -1 }` | **Compound** | **Optimizes complex Dashboard queries (RF10)**, filtering by `status` (e.g., 'InProgress') and sorting by date (newest/oldest). |
| `{ clientId: 1 }` | Simple | Fast lookup for a client's full repair history. |
| `{ mechanicsIds: 1 }` | Simple | Fast lookup for a mechanic's assigned tasks (Dashboard). |

---

## 6. Collection: `invoices`

Stores finalized, immutable billing records. This collection **"snapshots"** (copies) data from `workOrders` to ensure fiscal integrity (RNF05).

### Schema Definition

| Field | Type | Required | Description |
| :--- | :--- |:---------| :--- |
| `_id` | `ObjectId` | ✓        | Unique document identifier. |
| `invoiceNumber` | `String` | ✓        | Sequential, official invoice number (e.g., "FT 2025/1"). |
| `invoiceDate` | `ISODate` | ✓        | Date the invoice was officially emitted. |
| `status` | `String` | ✓        | Enum: `Emitted`, `Paid`, `Canceled`. |
| `workOrderId` | `ObjectId` | ✓        | **Reference** to the source `workOrders._id`. |
| `clientId` | `ObjectId` | ✓        | **Reference** to the `clients._id`. |
| `clientDetails` | `Object` | ✓        | **Snapshot** of client data at the time of invoicing. |
| `vehicleDetails` | `Object` | ✓        | **Snapshot** of vehicle data at the time of invoicing. |
| `items` | `Array` | ✓        | **Snapshot** (deep copy) of the `items` array from the work order. |
| `totalWithoutIVA` | `Decimal128` | ✓        | **Snapshot** of the final total. |
| `totalIVA` | `Decimal128` | ✓        | **Snapshot** of the final total. |
| `totalWithIVA` | `Decimal128` | ✓        | **Snapshot** of the final total. |
| `createdAt` | `ISODate` | ✓        | Timestamp when the invoice was created. |
| `updatedAt` | `ISODate` | ✓        | Timestamp (e.g., when moving `status` to `Paid`). |
| **`emittedById`** | **`String (UUID)`** | ✓        | **Reference to the user (PostgreSQL) who emitted the invoice.** |

### Business Logic (Application Layer)

* **RB01 Implementation:** The application layer (backend) **must** verify that a `workOrder` has a `status` of `Completed` *before* it allows the creation of a corresponding `invoice` document.

### Indexes

| Field(s) | Type | Purpose |
| :--- | :--- | :--- |
| `{ invoiceNumber: 1 }` | **Unique** | Ensures no duplicate invoice numbers (fiscal requirement). |
| `{ workOrderId: 1 }` | **Unique** | Ensures a work order can only be invoiced once. |
| `{ clientId: 1 }` | Simple | Fast lookup for all invoices for a specific client. |
| `{ invoiceDate: -1 }` | Simple | Fast sorting for financial reports (newest first). |

---

## 7. Collection: `appointments`

Stores all service bookings and manages the workshop's agenda (RF02).

### Schema Definition

| Field | Type | Required | Description                                                               |
| :--- | :--- |:---------|:--------------------------------------------------------------------------|
| `_id` | `ObjectId` | ✓        | Unique document identifier.                                               |
| `clientId` | `ObjectId` | ✓        | Reference to the `clients._id`.                                           |
| `appointmentDate` | `ISODate` | ✓        | Date and time of the scheduled booking.                                   |
| `vehicleId` | `ObjectId` |          | Reference to the `vehicles` collection.                                   |
| `workOrderId` | `ObjectId` |          | Reference to a `workOrder` (optional, e.g., for follow-ups).              |
| `notes` | `String` |          | Client notes or service to be performed.                                  |
| `status` | `String` | ✓        | Enum: `Scheduled`, `Completed`, `Canceled`.                                      |
| `createdAt` | `ISODate` | ✓        | Timestamp when the invoice was created.                                   |
| `updatedAt` | `ISODate` | ✓        | Timestamp of the last update.                       |

### Indexes

| Field(s) | Type         | Purpose |
| :--- |:-------------| :--- |
| `{ appointmentDate: -1 }` | **Simple**   |Fast lookup/sort for the agenda (newest first). |
| `{ clientId: 1 }` | **Simple**   | Fast lookup for a client's appointment history. |
| `{ status: 1, appointmentDate: 1 }` | **Compound** | Optimizes Dashboard/Agenda queries (RF10), filtering by status (e.g., 'Scheduled') and sorting by date. |

---

## 8. PostgreSQL User Integration (The "Hydration" Contract)

**This section defines the "contract" for handling user data, as specified in RNF02.**

This MongoDB database **does not** store any user details (like names, emails, or roles) to maintain a single source of truth and respect the separation of concerns. User management is handled entirely by the separate PostgreSQL database and Authentication service.

* **Strategy:** Fields such as `workOrders.mechanicsIds`, `workOrders.createdById`, and `invoices.emittedById` store the user's `UUID` (as a `String` type) from the PostgreSQL `users` table.

* **The "Contract":** The backend service is responsible for **"data hydration"**. When a user's name is needed (e.g., displaying the mechanic's name on a work order in the UI), the StArranja service **must** query the User/Auth API using the stored UUID to fetch the user's current details. The MongoDB database *only* stores the reference ID.