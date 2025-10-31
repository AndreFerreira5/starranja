/*
 * =================================================================
 * StArranja Database Setup Script
 * =================================================================
 * This script creates the database, collections, validation schemas,
 * and all performance and business rule indexes.
 *
 * This script is executed with the command:
 * mongosh "mongodb-url/starranja" --file database-mongo-setup.js
 */


print("Starting the StArranja database setup");

/*
 * =================================================================
 * Collection: clients
 * =================================================================
 */
db.createCollection("clients");

db.runCommand({
  collMod: "clients",
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["name", "nif", "phone", "createdAt", "updatedAt"],
      properties: {
        name: {
          bsonType: "string",
          description: "must be a string and is required"
        },
        nif: {
          bsonType: "string",
          pattern: "^[0-9]{9}$",
          description: "must be a string 9 digits long and is required"
        },
        phone: {
          bsonType: "string",
          description: "must be a string and is required"
        },
        email: {
          bsonType: "string",
          pattern: "^.+@.+\\..+$",
          description: "must be a valid email address"
        },
        address: {
          bsonType: "object",
          properties: {
            street: { bsonType: "string" },
            city: { bsonType: "string" },
            zipCode: { bsonType: "string" }
          }
        },
        createdAt: { bsonType: "ISODate" },
        updatedAt: { bsonType: "ISODate" }
      }
    }
  },
  validationAction: "error"
});

db.clients.createIndex(
  { nif: 1 },
  { unique: true }
);
db.clients.createIndex(
  { phone: 1 }
);
db.clients.createIndex(
  { email: 1 },
  { unique: true, partialFilterExpression: { email: { $exists: true } } }
);

print("Collection 'clients' created with validation and indexes.");

/*
 * =================================================================
 * Collection: vehicles
 * =================================================================
 */
db.createCollection("vehicles");

db.runCommand({
  collMod: "vehicles",
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["clientId", "licensePlate", "brand", "model", "createdAt", "updatedAt"],
      properties: {
        clientId: {
          bsonType: "objectId",
          description: "must be an ObjectId and is required"
        },
        licensePlate: {
          bsonType: "string",
          description: "must be a string and is required"
        },
        brand: {
          bsonType: "string",
          description: "must be a string and is required"
        },
        model: {
          bsonType: "string",
          description: "must be a string and is required"
        },
        vin: {
          bsonType: "string",
          pattern: "^[A-HJ-NPR-Z0-9]{17}$",
          description: "must be a 17-character VIN string (optional)"
        },
        lastKnownKilometers: {
          bsonType: "int",
          minimum: 0,
          description: "must be a non-negative integer (optional)"
        },
        createdAt: { bsonType: "ISODate" },
        updatedAt: { bsonType: "ISODate" }
      }
    }
  },
  validationAction: "error"
});

db.vehicles.createIndex(
  { licensePlate: 1 },
  { unique: true }
);
db.vehicles.createIndex(
  { clientId: 1 }
);
db.vehicles.createIndex(
  { vin: 1 },
  {
    unique: true,
    partialFilterExpression: { vin: { $exists: true } }
  }
);

print("Collection 'vehicles' created with validation and indexes.");

/*
 * =================================================================
 * Collection: workOrders
 * =================================================================
 */
db.createCollection("workOrders");

db.runCommand({
  collMod: "workOrders",
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: [
        "workOrderNumber",
        "clientId",
        "vehicleId",
        "status",
        "isActive",
        "entryDate",
        "createdAt",
        "updatedAt",
        "createdById"
      ],
      properties: {
        workOrderNumber: {
          bsonType: "string",
          description: "Sequential work order number is required."
        },
        clientId: { bsonType: "objectId" },
        vehicleId: { bsonType: "objectId" },
        mechanicsIds: {
          bsonType: "array",
          items: { bsonType: "string" }
        },
        createdById: {
          bsonType: "string",
          description: "User UUID (from PostgreSQL) who created the WO."
        },
        status: {
          enum: ["Draft", "AwaitingApproval", "Approved", "AwaitingParts", "InProgress", "Completed", "Invoiced", "Delivered"],
          description: "Must be one of the predefined status values."
        },
        isActive: {
            bsonType: "bool",
            description: "True if the WO is active (not completed/canceled/invoiced). Controls RB02."
        },
        quote: {
          bsonType: "object",
          required: ["isApproved"],
          properties: {
            clientObservations: { bsonType: "string" },
            diagnostic: { bsonType: "string" },
            isApproved: { bsonType: "bool" },
            totalPriceWithoutIVA: { bsonType: "decimal128" },
            totalPriceWithIVA: { bsonType: "decimal128" }
          }
        },
        items: {
          bsonType: "array",
          items: {
            bsonType: "object",
            required: ["type", "description", "quantity", "unitPriceWithoutIVA", "reference"],
            properties: {
              type: { enum: ["Part", "Labor"] },
              description: { bsonType: "string" },
              reference: { bsonType: "string" },
              quantity: { bsonType: "decimal128", minimum: 0 },
              unitPriceWithoutIVA: { bsonType: "decimal128" },
              ivaRate: { bsonType: "decimal128" },
              totalPriceWithIVA: { bsonType: "decimal128" }
            }
          }
        },
        finalTotalPriceWithoutIVA: { bsonType: "decimal128" },
        finalTotalIVA: { bsonType: "decimal128" },
        finalTotalPriceWithIVA: { bsonType: "decimal128" },
        // Timestamps
        createdAt: { bsonType: "ISODate" },
        updatedAt: { bsonType: "ISODate" },
        entryDate: { bsonType: "ISODate" },
        diagnosisRegisteredAt: { bsonType: ["ISODate", "null"] },
        quoteApprovedAt: { bsonType: ["ISODate", "null"] },
        executionStartedAt: { bsonType: ["ISODate", "null"] },
        completedAt: { bsonType: ["ISODate", "null"] },
        notificationSentAt: { bsonType: ["ISODate", "null"] },
        deliveredAt: { bsonType: ["ISODate", "null"] }
      }
    }
  },
  validationAction: "error"
});

// --- Indexes of workOrders ---

// Index for Business Rule RB02
db.workOrders.createIndex(
  { vehicleId: 1 },
  {
    unique: true,
    partialFilterExpression: {
        isActive: true
    }
  }
);
// Index for searching by number
db.workOrders.createIndex(
  { workOrderNumber: 1 },
  { unique: true }
);
// Index for Dashboard by status
db.workOrders.createIndex(
  { status: 1 }
);
// Index for Dashboard by entry date
db.workOrders.createIndex(
  { entryDate: -1 }
);
// Composite Index for Dashboard (status + data)
db.workOrders.createIndex(
  { status: 1, entryDate: -1 }
);
// Index for customer history
db.workOrders.createIndex(
  { clientId: 1 }
);
// Index for Mechanics Dashboard
db.workOrders.createIndex(
  { mechanicsIds: 1 }
);

print("Collection 'workOrders' created with validation and all indexes.");

/*
 * =================================================================
 * Collection: invoices
 * =================================================================
 */
db.createCollection("invoices");

db.runCommand({
  collMod: "invoices",
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: [
        "invoiceNumber",
        "invoiceDate",
        "status",
        "workOrderId",
        "clientId",
        "clientDetails",
        "vehicleDetails",
        "items",
        "totalWithIVA",
        "createdAt",
        "updatedAt",
        "emittedById"
      ],
      properties: {
        invoiceNumber: { bsonType: "string" },
        invoiceDate: { bsonType: "ISODate" },
        status: { enum: ["Emitted", "Paid", "Canceled"] },
        workOrderId: { bsonType: "objectId" },
        clientId: { bsonType: "objectId" },
        emittedById: {
          bsonType: "string",
          description: "User UUID (from PostgreSQL) who emitted the invoice."
        },
        clientDetails: {
          bsonType: "object",
          required: ["name", "nif", "address"],
          properties: {
            name: { bsonType: "string" },
            nif: { bsonType: "string" },
            address: { bsonType: "object" }
          }
        },
        vehicleDetails: {
          bsonType: "object",
          required: ["licensePlate"],
          properties: {
            licensePlate: { bsonType: "string" },
            brand: { bsonType: "string" },
            model: { bsonType: "string" }
          }
        },
        items: {
          bsonType: "array",
          minItems: 1,
          items: {
            bsonType: "object",
            required: ["description", "quantity", "unitPriceWithoutIVA"]
          }
        },
        totalWithoutIVA: { bsonType: "decimal128" },
        totalIVA: { bsonType: "decimal128" },
        totalWithIVA: { bsonType: "decimal128" },
        createdAt: { bsonType: "ISODate" },
        updatedAt: { bsonType: "ISODate" }
      }
    }
  },
  validationAction: "error"
});

db.invoices.createIndex(
  { invoiceNumber: 1 },
  { unique: true }
);
db.invoices.createIndex(
  { workOrderId: 1 },
  { unique: true }
);
db.invoices.createIndex(
  { clientId: 1 }
);
db.invoices.createIndex(
  { invoiceDate: -1 }
);

print("Collection 'invoices' created with validation and indexes.");

/*
 * =================================================================
 * Collection: appointments
 * =================================================================
 */

db.createCollection("appointments");

db.runCommand({
  collMod: "appointments",
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["clientId", "appointmentDate", "status", "createdAt", "updatedAt"],
      properties: {
        clientId: {
          bsonType: "objectId",
          description: "Reference to the client who made the appointment"
        },
        appointmentDate: {
          bsonType: "ISODate",
          description: "Date and time of the booking"
        },
        vehicleId: {
          bsonType: "objectId",
          description: "Optional reference to the vehicle"
        },
        workOrderId: {
          bsonType: "objectId",
          description: "Optional reference to a work order (e.g., follow-up)"
        },
        notes: {
          bsonType: "string",
          description: "Client notes or service to be performed"
        },
        status: {
          enum: ["Scheduled", "Completed", "Canceled"],
          description: "Status of the appointment"
        },
        createdAt: { bsonType: "ISODate" },
        updatedAt: { bsonType: "ISODate" }
      }
    }
  },
  validationAction: "error"
});

db.appointments.createIndex({ appointmentDate: -1 });
db.appointments.createIndex({ clientId: 1 });
db.appointments.createIndex({ status: 1, appointmentDate: 1 });

print("Collection 'appointments' created successfully.");

print("\n--- StArranja Database Setup Complete ---");