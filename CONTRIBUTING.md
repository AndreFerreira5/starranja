## Development Workflow

Here we follow a development sequence to maintain code organization and prevent dependencies:

1. **Develop [Models](src/models)** - Start by creating data models and schemas (you can check the DB diagrams [here](docs/))
    - Define your model structure
    - Add validation rules if applicable

2. **Develop [Database Interfacing Files](src/db)** - Build the interaction layer between our backend and the database
    - Implement CRUD operations agains the existing databases (using the previously created models)
   
3. **Develop [Routes](src/routes)** - Implement API endpoints after models and DB layer are ready
    - Use the DB interfacing files
    - Request/response handling
   
This order ensures a steady and compatible workflow, because the models represent the DB tables, while the DB interfacing
 layer depends on the models and interacts with the DB itself, and the routes depending on both the models and the DB interfaces.