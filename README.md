
# dq_llm - Data Query Language Model Microservice

`dq_llm` is a microservice designed to facilitate communication with data sources within the DQ Platform ecosystem. It leverages TaskWeaver, a dynamic task execution framework, to interpret and execute queries against various data sources, enhancing the platform's data querying capabilities.

## Setup

The setup for `dq_llm` is straightforward, leveraging Poetry for dependency management and package installation. To get started, follow these steps:

1. Install Poetry:

    ```bash
    pip install poetry
    ```

2. Clone the repository and navigate to the project directory:

    ```bash
    git clone <repository-url>
    cd dq_llm
    ```

3. Install project dependencies with Poetry:

    ```bash
    poetry install
    ```

4. Install TaskWeaver from the local package directory:

    ```bash
    pip install -e pkgs/TaskWeaver
    ```

5. Activate the Poetry shell:

    ```bash
    poetry shell
    ```

6. Start the `dq_llm` server:

    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 6545 --reload
    ```

## Project Structure

The project is structured as follows:
```
dq_llm/
├── app/
│   ├── api/
│   ├── core/
│   ├── db/
│   └── utils/
├── pkgs/
│   └── TaskWeaver/
├── project/
│   ├── codeinterpreter_examples/
│   ├── planner_examples/
│   └── plugins/
├── tests/
├── docker-compose.yml
├── Dockerfile
├── poetry.lock
├── pyproject.toml
└── README.md
```

The `plugins` directory under `project` contains TaskWeaver plugins specific to the `dq_llm` service. For more detailed information on these plugins and how to work with TaskWeaver, please refer to [TaskWeaver's documentation](https://microsoft.github.io/TaskWeaver/).

## Docker Support

This project includes Docker and Docker Compose configurations for containerized deployment:

- To build the Docker image:

    ```bash
    docker build -t dq_llm .
    ```

- To start the service using Docker Compose:

    ```bash
    docker-compose up
    ```

## Contributing

Contributions to `dq_llm` are welcome! Please refer to the `CONTRIBUTING.md` file in the TaskWeaver repository for guidelines on how to contribute.

## License

`dq_llm` is licensed under [MIT License](LICENSE). TaskWeaver is subject to its own licenses and copyright terms as detailed in its repository.


